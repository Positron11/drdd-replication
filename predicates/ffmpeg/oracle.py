import os
import subprocess

from tempfile    import TemporaryDirectory as TempDir
from pathlib     import Path
from core.oracle import Oracle
from core.config import Config, require


_SHM      = shm if (shm := Path("/dev/shm")).is_dir() else None
_LIB      = Path(__file__).resolve().parent / "lib"
_ASAN_ENV = { **os.environ, "ASAN_OPTIONS": "halt_on_error=1" }


class FFmpegOracle(Oracle[int]):
	"""Oracle that runs an ASAN-instrumented ffmpeg binary."""

	def __init__(self, config:Config) -> None:
		super().__init__()

		self._ffmpeg = require(

			path = _LIB / f"ffmpeg_g-{config['commit']}",
			hint = "make -C predicates/ffmpeg",

		)

		self._filter          = config["filter"]
		self._target          = config["target"]
		self._timeout         = config.get("timeout", 30.0)
		self._tmp_dir:TempDir = None    # type: ignore[assignment]
		self._tmp_path:Path   = None    # type: ignore[assignment]
		self._out_path:Path   = None    # type: ignore[assignment]
		self._cmd:list[str]   = None    # type: ignore[assignment]


	def __enter__(self) -> "FFmpegOracle":
		"""Create a per-oracle scratch dir for the input and output files."""

		self._tmp_dir  = TempDir(dir=_SHM, prefix="dd_")
		tmp_dir_path   = Path(self._tmp_dir.name)
		self._tmp_path = tmp_dir_path / "input"
		self._out_path = tmp_dir_path / f"out{self._target}"

		self._cmd = [

			str(self._ffmpeg),

			"-nostdin",
			"-y",
			"-i",                      str(self._tmp_path),
			"-threads",                "1",
			"-filter_complex_threads", "1",
			"-filter_complex",         self._filter,

			str(self._out_path),

		]

		return self


	def _call(self, candidate) -> bool:
		"""Reproduces iff ffmpeg trips AddressSanitizer on the candidate."""

		self._tmp_path.write_bytes(bytes(candidate))

		try:
			proc = subprocess.run(self._cmd,

				stdout  = subprocess.DEVNULL,
				stderr  = subprocess.PIPE,
				env     = _ASAN_ENV,
				timeout = self._timeout,

			)

		# operational failure (timeout, exec/IO error) -> treat as non-reproduction (?->X)
		except (subprocess.SubprocessError, OSError):
			return False

		return b"Sanitizer" in proc.stderr


	def __exit__(self, *_) -> None:
		"""Remove the scratch dir."""

		if self._tmp_dir is not None: self._tmp_dir.cleanup()

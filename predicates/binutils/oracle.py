import signal as _signal
import subprocess

from tempfile    import TemporaryDirectory as TempDir
from pathlib     import Path
from core.oracle import Oracle
from core.config import Config, require
from core.errors import ConfigError


_SHM = shm if (shm := Path("/dev/shm")).is_dir() else None
_LIB = Path(__file__).resolve().parent / "lib"


class BinutilsOracle(Oracle[int]):
	"""Oracle that runs a binary against a byte candidate and checks for a crash or needle."""

	def __init__(self, config:Config) -> None:
		super().__init__()

		signal = config.get("signal")
		needle = config.get("needle", "").encode() or None

		if (signal is None) == (needle is None): raise ConfigError("exactly one of 'signal' or 'needle' must be set")

		self._binary = require(

			path = _LIB / f"{config['binary']}-{config['commit']}",
			hint = "make -C predicates/binutils",

		)
		
		self._argv            = list(config["argv"])
		self._timeout         = config.get("timeout", 10.0)
		self._signum          = signal and getattr(_signal, signal)
		self._needle          = needle
		self._tmp_dir:TempDir = None    # type: ignore[assignment]
		self._tmp_path:Path   = None    # type: ignore[assignment]
		self._cmd:list[str]   = None    # type: ignore[assignment]


	def __enter__(self) -> "BinutilsOracle":
		"""Create per-oracle scratch dir (contains tool temp files e.g. objcopy 'st*')."""

		self._tmp_dir  = TempDir(dir=_SHM, prefix="dd_")
		self._tmp_path = Path(self._tmp_dir.name) / "input"
		self._cmd      = ["setarch", "-R", str(self._binary), *self._argv, str(self._tmp_path)]

		return self


	def _purge_scratch(self) -> None:
		"""Remove anything the tool left behind this call (e.g. objcopy scratch files)."""

		for p in self._tmp_path.parent.iterdir():
			if p == self._tmp_path: continue

			try: p.unlink()
			except OSError: pass


	def _call(self, candidate) -> bool:
		"""Reproduces iff the tool dies on the target signal or emits the needle."""

		self._tmp_path.write_bytes(bytes(candidate))

		try:
			proc = subprocess.run(self._cmd,

				stdout  = subprocess.DEVNULL,
				stderr  = subprocess.PIPE,
				timeout = self._timeout,

			)

		# operational failure (timeout, exec/IO error) -> treat as non-reproduction (?->X)
		except (subprocess.SubprocessError, OSError):
			self._purge_scratch()

			return False

		try:
			if self._signum is not None: return proc.returncode == -self._signum

			return self._needle in proc.stderr    # type: ignore[operator]

		finally: self._purge_scratch()


	def __exit__(self, *_) -> None:
		"""Remove the scratch dir."""

		if self._tmp_dir is not None: self._tmp_dir.cleanup()

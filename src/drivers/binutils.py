import signal as _signal
import subprocess
import tempfile

from importlib       import import_module
from pathlib         import Path
from algos           import ALGORITHMS
from core.oracle     import Oracle
from drivers.logging import MinimizerLog


_SHM       = shm if (shm := Path("/dev/shm")).is_dir() else None
_BINARY_P0 = 0.8


class BinutilsOracle(Oracle[int]):
	"""Oracle that runs a binary against a byte candidate and checks for a crash or needle."""

	def __init__(self,
		binary_path:Path,
		argv       :list[str],
		timeout    :float        = 10.0,
		signal     :str | None   = None,
		needle     :bytes | None = None,
		stream     :str          = "stderr") -> None:

		super().__init__()

		if (signal is None) == (needle is None):
			raise ValueError("Exactly one of 'signal' or 'needle' must be set")

		if stream not in ("stdout", "stderr", "both"):
			raise ValueError(f"Invalid stream: {stream!r}")

		self._binary        = binary_path
		self._argv          = list(argv)
		self._timeout       = timeout
		self._signum        = getattr(_signal, signal) if signal else None
		self._needle        = needle
		self._stream        = stream
		self._tmp_dir_ctx:tempfile.TemporaryDirectory = None  # type: ignore[assignment]
		self._tmp_dir :Path = None         # type: ignore[assignment]
		self._tmp_path:Path = None         # type: ignore[assignment]
		self._cmd:list[str] = None         # type: ignore[assignment]


	def __enter__(self) -> "BinutilsOracle":
		"""Create per-oracle scratch dir (contains tool temp files e.g. objcopy 'st*')."""

		self._tmp_dir_ctx = tempfile.TemporaryDirectory(dir=_SHM, prefix="dd_")
		self._tmp_dir     = Path(self._tmp_dir_ctx.name)
		self._tmp_path    = self._tmp_dir / "input"
		self._tmp_path.touch()
		self._cmd         = [str(self._binary), *self._argv, str(self._tmp_path)]

		return self


	def _purge_scratch(self) -> None:
		"""Remove anything the tool left behind this call (e.g. objcopy scratch files)."""

		for p in self._tmp_dir.iterdir():
			if p == self._tmp_path: continue

			try: p.unlink()
			except (OSError, IsADirectoryError): pass


	def _call(self, candidate) -> bool:
		self._tmp_path.write_bytes(bytes(candidate))

		try:
			proc = subprocess.run(self._cmd,

				stdout  = subprocess.PIPE,
				stderr  = subprocess.PIPE,
				timeout = self._timeout,

			)

		except subprocess.TimeoutExpired:
			self._purge_scratch()

			return False

		try:
			if self._signum is not None:
				return proc.returncode == -self._signum

			assert self._needle is not None         # invariant from __init__

			haystack = {
				"stdout": proc.stdout,
				"stderr": proc.stderr,
				"both"  : proc.stdout + proc.stderr,
			}[self._stream]

			return self._needle in haystack

		finally: self._purge_scratch()


	def __exit__(self, *_) -> None:
		"""Clean up temporary resources."""

		self._tmp_dir_ctx.cleanup()


def binutils_minimizer(
	input_path :Path,
	algorithm  :str,
	binary_path:Path,
	argv       :list[str],
	timeout    :float               = 10.0,
	signal     :str | None          = None,
	needle     :bytes | None        = None,
	stream     :str                 = "stderr",
	output_path:Path | None         = None,
	log        :MinimizerLog | None = None) -> dict:

	"""Run a DD minimization over a BinutilsOracle."""

	if algorithm not in ALGORITHMS: raise ValueError(f"Unknown algorithm '{algorithm}'. Available: {', '.join(ALGORITHMS)}")

	original = input_path.read_bytes()
	minimize = getattr(import_module(f"algos.{algorithm}"), "minimize")

	oracle = BinutilsOracle(

		binary_path = binary_path,
		argv        = argv,
		timeout     = timeout,
		signal      = signal,
		needle      = needle,
		stream      = stream,

	)

	if log: log.bind(len(original), oracle)

	# initialize probabilistic models
	kwargs = {"p_0": _BINARY_P0} if algorithm in ("cdd", "probdd") else {}

	with oracle:
		minimized = minimize(

			target = original,
			oracle = oracle,
			log    = log,

			**kwargs,

		)

	if output_path: output_path.write_bytes(bytes(minimized))

	return {
		"minimized_length"  : len(minimized),
		"oracle_invocations": oracle.calls,
	}

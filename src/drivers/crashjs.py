import json
import os
import subprocess
import tempfile

from importlib       import import_module
from pathlib         import Path
from algos           import ALGORITHMS
from core.oracle     import Oracle
from drivers.logging import MinimizerLog


_SHM       = shm if (shm := Path("/dev/shm")).is_dir() else None
_BINARY_P0 = 0.45


class CrashJSError(Exception):
	"""Worker process protocol or startup error."""


class MochaSession:
	"""Persistent stdin/stdout pipe to a long-lived `node worker.mjs` process.

	Each query() writes the candidate bytes to a per-session tempfile inside
	the lib/ tree (so ../instrumented/lodash/* relative imports resolve), then
	asks the worker to import + run the file. Worker uses ?t=<counter> cache
	busting so a freshly mutated candidate is never served from ESM cache.
	"""

	def __init__(self, lib_path:Path) -> None:
		self._lib_path              = lib_path
		self._proc:subprocess.Popen = None         # type: ignore[assignment]
		self._tmp_path:Path         = None         # type: ignore[assignment]


	def __enter__(self) -> "MochaSession":
		
		# stage tempfile inside lib/ so relative ../instrumented imports resolve
		stage_dir = self._lib_path / "case-staging"
		stage_dir.mkdir(exist_ok=True)

		fd, tmp = tempfile.mkstemp(dir=stage_dir, prefix="dd_", suffix=".spec.js")
		os.close(fd)
		self._tmp_path = Path(tmp)

		self._proc = subprocess.Popen(

			args   = ["node", "worker.mjs"],
			stdin  = subprocess.PIPE,
			stdout = subprocess.PIPE,
			cwd    = str(self._lib_path),
			text   = True,
			bufsize= 1,
			env    = {**os.environ, "NODE_NO_WARNINGS": "1"},

		)

		# read ready handshake
		line = self._proc.stdout.readline()    # type: ignore[union-attr]

		if not line: raise CrashJSError("worker did not produce a ready line")

		ready = json.loads(line)
		if not ready.get("ready"): raise CrashJSError(f"worker reported {ready}")

		return self


	def query(self, candidate:bytes) -> dict:
		"""Write candidate to staged tempfile and ask worker to run it."""

		self._tmp_path.write_bytes(candidate)

		assert self._proc.stdin is not None and self._proc.stdout is not None

		self._proc.stdin.write(str(self._tmp_path) + "\n")
		self._proc.stdin.flush()

		line = self._proc.stdout.readline()

		if not line: raise CrashJSError("worker closed stdout unexpectedly")

		return json.loads(line)


	def __exit__(self, *_) -> None:
		if self._proc is None: return

		try:
			if self._proc.stdin is not None: self._proc.stdin.close()
		except OSError: pass

		try: self._proc.wait(timeout=5)

		except subprocess.TimeoutExpired:
			try: self._proc.kill()
			except OSError: pass

			try: self._proc.wait(timeout=2)
			except subprocess.TimeoutExpired: pass

		self._tmp_path.unlink(missing_ok=True)
		self._tmp_path = None         # type: ignore[assignment]
		self._proc     = None         # type: ignore[assignment]


class CrashJSOracle(Oracle[int]):
	"""Oracle that runs a JS test file in mocha-free worker, matches against expected crash signature."""

	def __init__(self,
		lib_path :Path,
		err_type :str,
		err_msg  :str,
		top_file :str,
		timeout  :float = 10.0) -> None:

		super().__init__()

		self._lib_path             = lib_path
		self._err_type             = err_type
		self._err_msg              = err_msg
		self._top_file             = top_file
		self._timeout              = timeout
		self._session:MochaSession = None         # type: ignore[assignment]


	def __enter__(self) -> "CrashJSOracle":
		self._session = MochaSession(self._lib_path)
		self._session.__enter__()

		return self


	def _call(self, candidate) -> bool:
		try: result = self._session.query(bytes(candidate))

		except CrashJSError: return False

		# bug reproduces iff: failed AND signature matches expected
		return (
			not result["ok"]
			and result["errType"] == self._err_type
			and result["errMsg"]  == self._err_msg
			and result["topFile"] == self._top_file
		)


	def __exit__(self, *_) -> None:
		if self._session is not None:
			self._session.__exit__(None, None, None)

		self._session = None         # type: ignore[assignment]


def crashjs_minimizer(
	input_path :Path,
	algorithm  :str,
	lib_path   :Path,
	err_type   :str,
	err_msg    :str,
	top_file   :str,
	timeout    :float               = 10.0,
	output_path:Path | None         = None,
	log        :MinimizerLog | None = None) -> dict:

	"""Run a DD minimization over a CrashJSOracle."""

	if algorithm not in ALGORITHMS: raise ValueError(f"Unknown algorithm '{algorithm}'. Available: {', '.join(ALGORITHMS)}")

	original = input_path.read_bytes()
	minimize = getattr(import_module(f"algos.{algorithm}"), "minimize")

	oracle = CrashJSOracle(

		lib_path = lib_path,
		err_type = err_type,
		err_msg  = err_msg,
		top_file = top_file,
		timeout  = timeout,

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

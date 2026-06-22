from pathlib     import Path
from core.oracle import Oracle
from core.config import Config, require
from .session    import WorkerSession, WorkerError


_LIB = Path(__file__).resolve().parent / "lib"


class CrashJSOracle(Oracle[int]):
	"""Oracle that runs a JS test file in a Node worker, matches against expected crash signature."""

	def __init__(self, config:Config) -> None:
		super().__init__()

		lib = _LIB

		require(

			path = lib / "worker.mjs",
			hint = "make -C predicates/crashjs",

		)

		self._lib_path              = lib
		self._err_type              = config["errType"]
		self._err_msg               = config["errMsg"]
		self._top_file              = config["topFile"]
		self._timeout               = config.get("timeout", 10.0)
		self._session:WorkerSession = None    # type: ignore[assignment]


	def __enter__(self) -> "CrashJSOracle":
		"""Start the long-lived Node worker."""

		self._session = WorkerSession(self._lib_path)
		self._session.__enter__()

		return self


	def _call(self, candidate) -> bool:
		"""Reproduces iff the test fails with the expected (errType, errMsg, topFile)."""

		# a dead/timed-out worker is an operational failure -> non-reproduction (?->X)
		try: result = self._session.query(bytes(candidate), self._timeout)

		except WorkerError:
			return False

		return (

			not result["ok"]
			and result["errType"] == self._err_type
			and result["errMsg"]  == self._err_msg
			and result["topFile"] == self._top_file

		)


	def __exit__(self, *_) -> None:
		"""Tear down the worker session."""

		if self._session is not None: self._session.__exit__(None, None, None)

		self._session = None    # type: ignore[assignment]

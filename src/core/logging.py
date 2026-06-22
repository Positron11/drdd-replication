import sys
import time

from math   import inf
from typing import TextIO


class Log:
	"""Base logger: writes (optionally transient) lines to a stream."""

	def __init__(self, stream:TextIO=sys.stdout) -> None:
		self._stream = stream
		self._istty  = getattr(self._stream, "isatty", lambda: False)()


	def __call__(self, event) -> None: ...


	def _emit(self, line:str, commit:bool=True) -> None:
		"""Write a log line - on TTY, overwrite current line and clear tail."""

		# transient lines are pointless on a non-TTY stream
		if not commit and not self._istty: return

		# \r: back to column 0 | \x1b[K: erase to end of line
		if self._istty: line = f"\r{line}\x1b[K"

		print(line,

			end   = "\n" if commit else "",
			file  = self._stream,
			flush = True

		)


	def flush(self) -> None: ...


class RateLog(Log):
	"""Logger with time-based rate-limiting."""

	def __init__(self, stream:TextIO=sys.stdout, interval:float=inf) -> None:
		super().__init__(stream)

		self._interval   = interval
		self._last_edge  = time.perf_counter()
		self._last_event = None


	def __call__(self, event) -> None:
		"""Emit an update and commit on an interval tick or forced edge."""

		self._last_event = event

		now  = time.perf_counter()
		edge = self._force(event) or now - self._last_edge >= self._interval

		self._log(event, edge=edge)

		if edge: self._last_edge = now


	def _force(self, event) -> bool:
		"""Hook: subclasses may force an out-of-band commit."""

		return False


	def _log(self, event, edge:bool=False) -> None: ...


	def flush(self) -> None:
		"""Commit the most recent update immediately, bypassing the interval."""

		if self._last_event is not None: self._log(self._last_event, edge=True)

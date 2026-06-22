from math           import inf
from datetime       import datetime
from typing         import TextIO
from core.logging   import RateLog
from core.telemetry import Reading
from utils.fmt      import fmt_bytes, progress_bar, FILLER, DIVIDER


class StreamView(RateLog):
	"""Renders a minimization progress stream to a text stream (file or stdout), rate-limited."""

	def __init__(self,
			
			stream    :TextIO,
			input_size:int,
			interval  :float = inf) -> None:

		super().__init__(stream, interval)

		self._input_size   = input_size
		self._col_w        = len(fmt_bytes(input_size))
		self._last_subsize = -1


	def _log(self, event:Reading, edge:bool=False) -> None:
		"""Render the reading - transient on a TTY, committed on an edge."""

		pct = 100 * (1 - event.size / (self._input_size or 1))

		line = (

			f"{datetime.now().strftime('%H:%M:%S')}  "
			f"{progress_bar(pct)} {fmt_bytes(event.size):{FILLER}>{self._col_w + 3}}  {DIVIDER}  "
			f"chunk: {event.subsize:{FILLER}>{self._col_w}}   calls: {event.calls:{FILLER}>6}"

		)

		self._emit(line, edge)

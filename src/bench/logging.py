import time

from datetime        import datetime
from typing          import TextIO
from core.logging    import Log
from core.telemetry  import Reading
from runtime.logging import StreamView
from bench.results   import RunResult
from utils.fmt       import fmt_bytes, fmt_time, progress_bar, labelled_rule, fit, FILLER, DIVIDER


_SIZE_W    = 9
_CALLS_W   = 6
_REDUCER_W = 8
_LABEL_W   = 12
_LINE_W    = _SIZE_W + _CALLS_W + 18


class TerminalView(Log):
	"""Live single-line terminal view of one benchmark task."""

	def __init__(self,
			
			input_size :int,
			counter_str:str,
			reducer    :str,
			label      :str) -> None:

		super().__init__()

		self._input_size = input_size
		self._left       = f"{counter_str}  {DIVIDER}  {fit(reducer, _REDUCER_W)} -> {fit(label, _LABEL_W)}  {DIVIDER}"
		self._t0         = time.perf_counter()
		self._ts_start   = datetime.now().strftime("%H:%M:%S")

		placeholder = f"{fmt_bytes(input_size)}  starting..."

		self._log(f"{placeholder:<{_LINE_W}}", "00:00")


	def __call__(self, event:Reading) -> None:
		pct = 100 * (1 - event.size / (self._input_size or 1))
		ts  = fmt_time(time.perf_counter() - self._t0)

		self._log(f"{progress_bar(pct)} [{pct:{FILLER}>5.1f}%]  {event.calls:{FILLER}>{_CALLS_W}} calls", ts)


	def _log(self, content:str, ts:str, commit:bool=False) -> None:
		"""Render the task's status line (overwrite + tail-clear handled by _emit)."""

		self._emit(f"{self._left}  {content}  {DIVIDER}  {ts}", commit=commit)


	def done(self, result:RunResult) -> None:
		"""Commit the task's final line."""

		ts = f"{self._ts_start}-{datetime.now().strftime('%H:%M:%S')}"

		if result.minimized_length is not None:
			reduction = 100 * (1 - result.minimized_length / (self._input_size or 1))

			content = (

				f"{fmt_bytes(result.minimized_length):{FILLER}>{_SIZE_W}}   "
				f"{reduction:5.1f}%   "
				f"{result.calls:{FILLER}>{_CALLS_W}} calls"

			)

			self._log(content, ts, commit=True)

		elif result.error: self._log(labelled_rule(_LINE_W, "FAILED"), ts, commit=True)

		else: self._log("-  (no result)", ts, commit=True)


class FileView(StreamView):
	"""Per-task log file: a header, the rate-limited progress stream, and a result footer."""

	def __init__(self,
			
			stream    :TextIO,
			input_size:int,
			reducer   :str,
			label     :str,
			started   :datetime,
			interval  :float = 5.0) -> None:

		super().__init__(stream, input_size, interval)

		self._stream.write(f"predicate:  {label}\n")
		self._stream.write(f"reducer:    {reducer}\n")
		self._stream.write(f"input_size: {fmt_bytes(input_size)}\n")
		self._stream.write(f"started:    {started.isoformat()}\n\n")


	def _force(self, event:Reading) -> bool:
		"""Commit whenever the subset size changes - each new k marks a granularity transition."""

		changed            = event.subsize != self._last_subsize
		self._last_subsize = event.subsize

		return changed


	def done(self, result:RunResult) -> None:
		"""Write the result footer."""

		if result.error: self._stream.write(f"\n\n{result.error.upper()}\n")

		length = result.minimized_length if result.minimized_length is not None else "N/A"

		self._stream.write(f"\nminimized: {length} B\n")
		self._stream.write(f"oracle:      {result.calls} invocations\n")
		self._stream.write(f"elapsed:     {result.wall_time:.1f}s\n")

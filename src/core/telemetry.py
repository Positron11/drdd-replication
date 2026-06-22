from dataclasses import dataclass
from typing      import Callable
from core.oracle import Oracle


@dataclass(frozen=True, slots=True)
class Reading:
	"""A single minimization telemetry reading."""

	size   :int    # current best candidate length
	subsize:int    # granularity (subset size k)
	calls  :int    # oracle invocations so far


class TelemetryBus:
	"""Stamp oracle state onto readings and fan out."""

	def __init__(self, oracle:Oracle, *sinks:Callable[[Reading], None]) -> None:
		self._oracle = oracle
		self._sinks  = sinks


	def __call__(self, size:int, subsize:int) -> None:
		if not self._sinks: return

		reading = Reading(size, subsize, self._oracle.calls)

		for sink in self._sinks: sink(reading)

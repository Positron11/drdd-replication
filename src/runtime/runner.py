from typing         import Callable, Sequence
from core.oracle    import Oracle
from core.errors    import OracleError
from core.logging   import Log
from core.telemetry import TelemetryBus


def run_minimization(
		data   :bytes,
		reducer:Callable,
		oracle :Oracle,
		views  :Sequence[Log] = (),
		
		**kwargs) -> bytes:

	"""Minimize data against oracle with reducer."""

	bus = TelemetryBus(oracle, *views)

	with oracle:
		minimized = reducer(

			target = data,
			oracle = oracle,
			tick   = bus,

			**kwargs
		)

		# safety net: confirm the result still reproduces (uncounted)
		if not oracle(minimized, count=False):
			raise OracleError("minimized output no longer reproduces the predicate")

	for view in views: view.flush()

	return bytes(minimized)

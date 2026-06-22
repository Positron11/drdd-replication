from typing      import TypeVar, Callable
from core.oracle import Oracle
from reducers    import _noop


T = TypeVar("T")


def _complement_sweep(
	target     :list[T],
	granularity:int,
	oracle     :Oracle[T],
	tick       :Callable[[int, int], None] = _noop) -> tuple[list[T], int]:

	"""Identify benign chunks of target with variable granularity."""

	while len(target) >= 1:

		reduced = []
		tlen    = len(target)
		subsize = max(tlen // granularity, 1)
		restart = False

		for i in range(0, tlen, subsize):
			split      = i + subsize
			complement = reduced + target[split:]

			tick(len(reduced) + tlen - i, subsize)

			# causal restart
			if oracle(complement): 
				target      = complement
				granularity = max(granularity - 1, 2)
				restart     = True

				break
				
			reduced.extend(target[i:split])

		if not restart: return reduced, granularity

	# fall-through
	return list(target), granularity


def minimize(
	target:list[T],
	oracle:Oracle[T],
	tick  :Callable[[int, int], None] = _noop) -> list[T]:

	"""Classical Delta-Debugging as presented in the DebuggingBook."""

	minimized   = list(target)
	granularity = 2

	while True:
		minimized, granularity = _complement_sweep(minimized, granularity, oracle, tick)
		
		if granularity == len(minimized): break

		granularity = min(granularity * 2, len(minimized))

	return minimized

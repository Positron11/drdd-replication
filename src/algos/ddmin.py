from typing       import TypeVar
from core.oracle  import Oracle
from core.logging import RateLog


T = TypeVar("T")


def _complement_sweep(
	target     :list[T],
	granularity:int,
	oracle     :Oracle[T],
	log        :RateLog | None = None) -> tuple[list[T], int]:

	"""Identify benign chunks of target with variable granularity."""

	# range error guard
	while len(target) >= 2:
		
		reduced = []
		tlen    = len(target)
		subsize = tlen // granularity
		restart = False

		for i in range(0, tlen, subsize):
			split      = i + subsize
			complement = reduced + target[split:]

			if log: log(len(complement) + min(subsize, tlen - i), subsize, force=tlen - i <= subsize)

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
	log   :RateLog | None = None) -> list[T]:

	"""Classical Delta-Debugging as presented in the DebuggingBook."""

	minimized   = list(target)
	granularity = 2

	while True:
		minimized, granularity = _complement_sweep(minimized, granularity, oracle, log)
		
		if granularity == len(minimized): break

		granularity = min(granularity * 2, len(minimized))

	return minimized

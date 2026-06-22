from math        import log as ln
from typing      import TypeVar, Callable
from core.oracle import Oracle
from reducers    import _noop


T = TypeVar("T")

# decay base from "Probabilistic Delta Debugging" (Zhang et al.)
_DECAY_BASE = 1.582


def _compute_size(r:int, p_0:float, maxlen:int) -> int:
	"""Compute the subset size to use in the current round."""

	p = p_0 * (_DECAY_BASE ** r)
	
	# degenerate: probability model has broken down, use minimum size
	if p >= 1.0: return 1

	# closed-form argmax of s * (1-p)^s via f'(s) = 0
	s = -1.0 / ln(1.0 - p)

	return max(1, min(round(s), maxlen))


def _complement_sweep(
	target :list[T],
	subsize:int,
	oracle :Oracle[T],
	tick   :Callable[[int, int], None] = _noop) -> list[T]:

	"""Identify benign chunks of target with variable granularity."""

	reduced = []
	tlen    = len(target)

	for i in range(0, tlen, subsize):
		split      = i + subsize
		complement = reduced + target[split:]

		tick(len(reduced) + tlen - i, subsize)

		if not oracle(complement): reduced.extend(target[i:split])

	return reduced


def minimize(
	target:list[T],
	oracle:Oracle[T],
	p_0   :float                      = 0.1,
	tick  :Callable[[int, int], None] = _noop) -> list[T]:

	"""CDD algorithm over an ordered sequence."""

	minimized = list(target)
	
	r = 0

	while minimized:
		subsize   = _compute_size(r, p_0, len(minimized))
		minimized = _complement_sweep(minimized, subsize, oracle, tick)

		# simulate do-while
		if subsize <= 1: break
		
		r += 1

	return minimized

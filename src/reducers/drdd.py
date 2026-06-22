from typing      import TypeVar, Callable
from core.oracle import Oracle
from reducers    import _noop


T = TypeVar("T")


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


def _causal_chain_scan(
	target :list[T], 
	c_iters:int, 
	oracle :Oracle[T], 
	tick   :Callable[[int, int], None] = _noop) -> list[T]:

	reduced = list(target)

	for i in range(c_iters):
		_reduced = list(_complement_sweep(reduced, 1, oracle, tick))

		if _reduced == reduced: break

		reduced = _reduced

	return reduced


def minimize(
	target :list[T],
	oracle :Oracle[T],
	s_min  :int                        = 1, 
	s_max  :int | None                 = None,
	c_iters:int | None                 = None, 
	tick   :Callable[[int, int], None] = _noop) -> list[T]:

	"""Delta-Debugging with halving complement sweep over an ordered sequence."""

	minimized = list(target)
	subsize   = len(target)
	s_max     = s_max or subsize
	c_iters   = c_iters or subsize

	while subsize and minimized:
		subsize //= 2
		
		# bounded subset size
		if subsize >  s_max: continue
		if subsize <= s_min: break
		
		minimized = _complement_sweep(minimized, subsize, oracle, tick)

	return _causal_chain_scan(minimized, c_iters, oracle, tick)

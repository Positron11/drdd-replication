from typing         import TypeVar, Callable
from core.oracle    import Oracle
from reducers._tick import _noop


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


def causal_chain_scan(
	target :list[T],
	oracle :Oracle[T],
	c_iters:int | None                 = None,
	tick   :Callable[[int, int], None] = _noop) -> list[T]:

	"""Sweep single elements until a pass removes nothing, or `c_iters` passes run.

	Unbounded - the default - this reaches a fixed point, and the result is
	1-minimal: no single element can be dropped without losing reproduction. Each
	non-final pass strictly shrinks the candidate, so len(target) passes always
	suffice. A smaller bound is drdd's restart budget R, which trades that
	guarantee for oracle calls.

	Public because it is also the *check* for 1-minimality: the experiment
	scripts run it unbounded against a fresh oracle, and whatever it still
	removes is what a competitor left behind.
	"""

	reduced = list(target)

	for _ in range(c_iters if c_iters is not None else len(reduced)):
		_reduced = _complement_sweep(reduced, 1, oracle, tick)

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

	while subsize and minimized:
		subsize //= 2

		# bounded subset size
		if subsize >  s_max: continue
		if subsize <= s_min: break

		minimized = _complement_sweep(minimized, subsize, oracle, tick)

	return causal_chain_scan(minimized, oracle, c_iters, tick)

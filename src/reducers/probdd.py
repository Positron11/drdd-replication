import numpy as np

from typing      import TypeVar, Callable
from core.oracle import Oracle
from reducers    import _noop


T = TypeVar("T")


def _sort_indices(probs:np.ndarray, rng:np.random.Generator) -> np.ndarray:
	"""Sort active elements by probability in ascending order."""

	active = np.where(probs < 1.0)[0]

	# shuffle entire array
	rng.shuffle(active)

	# stable sort preserves shuffled order within same-p groups
	return active[np.argsort(probs[active], kind='stable')]


def _update_fail_probs(indices:np.ndarray, probs:np.ndarray) -> None:
	"""Update probabilities after a failed deletion attempt."""

	p_fail = float(np.prod(1.0 - probs[indices]))
	new_p  = np.minimum(probs[indices] / (1.0 - p_fail), 1.0)

	# clamp numerical noise from singleton updates to exact 1
	new_p[new_p > 1.0 - 1e-12] = 1.0

	probs[indices] = new_p


def _select_subset(probs:np.ndarray, rng:np.random.Generator) -> np.ndarray:
	"""Select a subset via probabilities to test for removal."""

	order     = _sort_indices(probs, rng)
	best_gain = -1.0
	best_size = 0
	p_pass    = 1.0

	for size, idx in enumerate(order, start=1):
		p_pass *= 1.0 - probs[idx]
		gain    = size * p_pass

		# keep extending until expected gain starts decreasing
		if gain > best_gain: best_gain, best_size = gain, size
		else:                 break

	return order[:best_size]


def minimize(
	target:list[T],
	oracle:Oracle[T],
	p_0   :float                      = 0.1,
	seed  :int                        = 0,
	tick  :Callable[[int, int], None] = _noop) -> list[T]:

	"""Probabilistic Delta-Debugging algorithm over an ordered sequence."""

	rng       = np.random.default_rng(seed)
	minimized = list(target)
	probs     = np.full(len(minimized), p_0, dtype=np.float64)

	while True:
		subset = _select_subset(probs, rng)

		# terminate when every remaining element has probability 1
		if not minimized or len(subset) == 0: break

		marked    = set(subset.tolist())
		candidate = [item for i, item in enumerate(minimized) if i not in marked]

		if oracle(candidate): # remove the attempted subset if it is removable
			minimized = candidate
			probs     = np.delete(probs, subset)

		# otherwise update probabilities of the attempted subset
		else: _update_fail_probs(subset, probs)

		tick(len(minimized), len(subset))

	return minimized

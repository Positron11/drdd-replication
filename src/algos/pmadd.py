from math         import exp
from random       import Random
from typing       import TypeVar
from core.oracle  import Oracle
from core.logging import RateLog


T = TypeVar("T")


def _confidence(mono:int) -> float:
	"""Compute the PMA confidence function."""

	# clamp exponent to prevent overflow
	return 1 / (1 + exp(-max(-709, min(709, mono))))


def _bits(pairs:list[tuple[int, T]]) -> int:
	"""Build an integer bitmap from a list of (index, item) pairs."""

	b = 0
	
	for idx, _ in pairs:
		b |= 1 << idx
	
	return b


def _check_dominated(candidate:int, history:list[int]) -> bool:
	"""Check whether a candidate is eligible to be skipped under monotonicity."""

	return any((candidate & prior) == candidate for prior in history)


def _history_insert(candidate:int, history:list[int]) -> None:
	"""Insert a non-interesting bitmask into the antichain history."""

	# prune entries now dominated by the new one (prior ⊆ candidate)
	history[:] = [p for p in history if (p & candidate) != p]
	
	history.append(candidate)


def _complement_sweep(
	target :list[tuple[int, T]],
	granularity:int,
	M      :int,
	history:list[int],
	oracle :Oracle[T],
	rng    :Random,
	log    :RateLog | None = None) -> tuple[list[tuple[int, T]], int, int]:

	"""Identify benign chunks of target with PMA-guided skipping."""

	# range error guard
	while len(target) >= 2:
		
		reduced      = []
		tlen         = len(target)
		subsize      = tlen // granularity
		target_bits  = _bits(target)
		removed_bits = 0
		restart      = False

		# test contiguous discrete subsets of size subsize
		for i in range(0, tlen, subsize):
			split      = i + subsize
			complement = reduced + target[split:]

			if log: log(len(complement) + min(subsize, tlen - i), subsize, force=tlen - i <= subsize)

			subset_bits    = _bits(target[i:split])
			candidate_bits = target_bits & ~(subset_bits | removed_bits)
			skip_eligible  = _check_dominated(candidate_bits, history)

			# PMA-guided skip
			if skip_eligible and _confidence(M) > rng.random(): interesting = False

			else:
				interesting = oracle([delta for _, delta in complement])			
				
				# monotonicity assessment
				if interesting:

					# interesting subset of non-interesting prior = violation
					if skip_eligible: M -= 1
					else:             M += 1

				# skip_eligible = false guarantees entry is not redundant
				if not (interesting or skip_eligible): _history_insert(candidate_bits, history)

			if interesting:
				target      = complement
				granularity = max(granularity - 1, 2)
				restart     = True

				break
			
			reduced.extend(target[i:split])

		if not restart: return reduced, granularity, M

	# fall-through
	return list(target), granularity, M


def minimize(
	target:list[T],
	oracle:Oracle[T],
	seed  :int            = 0,
	log   :RateLog | None = None) -> list[T]:

	"""PMA-enhanced Delta-Debugging algorithm over an ordered sequence."""

	rng         = Random(seed)
	minimized   = list(enumerate(target))
	granularity = 2

	history = []

	M = 0

	while True:
		minimized, granularity, M = _complement_sweep(

			target      = minimized,
			granularity = granularity,
			M           = M,
			history     = history,
			oracle      = oracle,
			rng         = rng,
			log         = log

		)

		if granularity == len(minimized): break

		granularity = min(granularity * 2, len(minimized))

	return [delta for _, delta in minimized]

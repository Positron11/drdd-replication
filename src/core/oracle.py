from abc    import ABC, abstractmethod
from typing import TypeVar, Generic, Sequence


T = TypeVar("T")


class Oracle(ABC, Generic[T]):
	"""Instrumented predicate oracle.

	Subclasses implement `_call`; stateful oracles also override `__enter__`/
	`__exit__` to acquire and release resources (servers, subprocesses).
	"""

	def __init__(self) -> None:
		self.calls = 0


	def __call__(self, candidate:Sequence[T], *, count:bool=True) -> bool:
		"""Update instrumentation and delegate to `_call`."""

		self.calls += count

		return self._call(candidate)


	def __enter__(self) -> "Oracle[T]":
		"""Acquire oracle resources - stateful oracles override this."""

		return self


	def __exit__(self, *_) -> None:
		"""Release oracle resources - stateful oracles override this."""


	@abstractmethod
	def _call(self, candidate:Sequence[T]) -> bool:
		"""Check whether candidate reproduces the target behavior."""

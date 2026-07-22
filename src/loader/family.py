from dataclasses import dataclass
from pathlib     import Path
from typing      import Callable
from core.oracle import Oracle
from core.config import Config
from core.errors import ConfigError


# a family's Oracle class, as consumers use it: called with a case's resolved
# Config, it yields the predicate instance for that case
OracleFactory = Callable[[Config], Oracle]


@dataclass(frozen=True)
class Case:
	"""One predicate instance: an input file and the config to run it under.

	`meta` is human-facing provenance the loader carries but never reads - a bug
	url, a crash summary - kept apart from `config`, which the oracle does read.
	"""

	id    :str
	path  :Path
	config:Config
	meta  :dict


@dataclass(frozen=True)
class Family:
	"""A loaded predicate family: its oracle, the cases that exercise it, and reducer tuning."""

	name  :str
	oracle:OracleFactory
	build :str | None
	cases :dict[str, Case]
	tuning:dict


	def case(self, id:str) -> Case:
		"""The case with `id`, validated."""

		if id not in self.cases: raise ConfigError(f"no case '{id}' in the '{self.name}' family")

		case = self.cases[id]

		if not case.path.exists(): raise ConfigError(f"input not found: {case.path}")

		return case

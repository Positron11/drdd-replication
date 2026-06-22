from dataclasses import dataclass
from pathlib     import Path
from typing      import Callable
from core.oracle import Oracle
from core.config import Config
from core.errors import ConfigError


# what a plugin's oracle.py hands back
OracleFactory = Callable[..., Oracle]


@dataclass(frozen=True)
class Case:
	"""One predicate instance: an input file and the config to run it under."""

	id    :str
	path  :Path
	config:Config


@dataclass(frozen=True)
class Family:
	"""A loaded predicate family: its oracle, the cases that exercise it, and reducer tuning."""

	name  :str
	oracle:OracleFactory
	cases :dict[str, Case]
	tuning:dict


	def case(self, id:str) -> Case:
		"""The case with `id`, validated."""

		if id not in self.cases: raise ConfigError(f"no case '{id}' in the '{self.name}' family")

		case = self.cases[id]

		if not case.path.exists(): raise ConfigError(f"input not found: {case.path}")

		return case

"""The reducers, and how a family's tuning reaches them.

Every non-underscore module here is a reducer and is expected to expose
`minimize`; the registry below discovers them, so a new one needs no
registration. Support code belongs behind a leading underscore, as `_tick` is.
"""

import inspect
import pkgutil

from importlib import import_module

from reducers._tick import _noop


# registry construction
REDUCERS = {

	name: import_module(f"{__name__}.{name}").minimize

	for name in sorted([

		i.name

		for i in pkgutil.iter_modules(__path__)
		if not i.name.startswith("_")

	])

}

# properties of a family's *inputs* that a manifest may declare. Not c_iters or
# seed - those are a reducer's own (the ablation axis, the reproducibility
# anchor), never a predicate's to set.
_PROPERTIES = {"p_0"}


def tuning_for(reducer:str, tuning:dict) -> dict:
	"""One reducer's share of a family's tuning.

	A family's `tuning` names properties of its inputs - `p_0`, how removable
	they are. A reducer receives a property iff it has a parameter for it, so
	probdd and cdd get `p_0` and the rest ignore it. Asking the signature is what
	keeps this honest: there is no roster of "the probabilistic ones" to drift
	out of step with the reducers themselves.
	"""

	params = inspect.signature(REDUCERS[reducer]).parameters

	return {k: v for k, v in tuning.items() if k in _PROPERTIES and k in params}


__all__ = ["REDUCERS", "tuning_for"]

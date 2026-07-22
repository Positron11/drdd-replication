"""The reducers.

Every non-underscore module here is a reducer and is expected to expose
`minimize`; the registry below discovers them, so a new one needs no
registration. Support code belongs behind a leading underscore, as `_tick` is.
"""

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

# reducers that expose p_0
PROBABILISTIC = ("probdd", "cdd")

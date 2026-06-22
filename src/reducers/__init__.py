import pkgutil

from importlib import import_module


def _noop(size:int, subsize:int) -> None:
	"""Default no-op progress callback used when no collector is attached."""


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

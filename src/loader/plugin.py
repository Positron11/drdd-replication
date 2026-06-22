import importlib.util
import json
import sys

from pathlib       import Path
from core.oracle   import Oracle
from core.config   import Config
from core.errors   import ConfigError
from loader.family import Family, Case, OracleFactory


_ORACLE   = "oracle.py"
_MANIFEST = "manifest.json"


# loaded plugins, keyed by oracle.py path (a plugin is imported at most once)
_loaded:dict[Path, OracleFactory] = {}


def _load_cases(dataset_dir:Path, data:dict) -> dict[str, Case]:
	"""Build the Cases from a parsed manifest, keyed by id.

	Each predicate gives its input `path`, relative to the dataset. Its config is
	the manifest `common` overlaid with the case's own. A predicate may declare
	auxiliary `files` its oracle needs, each a dataset-relative path resolved
	here and exposed in config under its own name.
	"""

	common = data.get("common", {})
	result = {}

	for p in data["predicates"]:

		# concatenate common and individual config
		config = Config({**common, **p.get("config", {})})

		# resolve any auxiliary files the predicate declares
		for name, rel in p.get("files", {}).items(): config[name] = dataset_dir / rel

		result[p["id"]] = Case(p["id"], dataset_dir / p["path"], config)

	return result


def _load_oracle(dataset_dir:Path) -> OracleFactory:
	"""Import a dataset's oracle.py as a plugin and return its Oracle subclass.

	The directory is loaded as a throwaway package (so the oracle's own
	`from .helper import ...` relative imports resolve against its own files).
	"""

	source = (dataset_dir / _ORACLE).resolve()

	if not source.is_file(): raise ConfigError(f"no {_ORACLE} in {dataset_dir}")
	if source in _loaded:    return _loaded[source]

	# load oracle.py as a one-off package so relative imports resolve
	pkg = f"dd_predicate_{dataset_dir.name}"
	
	# make the dir a package
	spec = importlib.util.spec_from_file_location(

		name                       = pkg, 
		location                   = source,
		submodule_search_locations = [str(dataset_dir)],

	)

	# always set: source is a verified file
	assert spec and spec.loader

	# register before exec so relative imports resolve
	module           = importlib.util.module_from_spec(spec)
	sys.modules[pkg] = module
	
	spec.loader.exec_module(module)

	# plugin contract: a single Oracle subclass defined in this file
	oracles = [
		
		obj for obj in vars(module).values()

		if isinstance(obj, type) 
		and issubclass(obj, Oracle) 
		and obj.__module__ == pkg
	
	]

	if len(oracles) != 1: raise ConfigError(f"{source} must define exactly one Oracle (found {len(oracles)})")

	_loaded[source] = oracles[0]

	return oracles[0]


def load_dataset(dataset_dir:Path) -> Family:
	"""Resolve a dataset directory into a Family."""

	manifest = dataset_dir / _MANIFEST

	if not manifest.is_file(): raise ConfigError(f"no dataset at {dataset_dir}")

	data = json.loads(manifest.read_text())

	return Family(
		
		name   = data["name"], 
		oracle = _load_oracle(dataset_dir), 
		cases  = _load_cases(dataset_dir, data), 
		tuning = data.get("tuning", {})
		
	)

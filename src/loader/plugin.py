import importlib.util
import json
import sys

from pathlib       import Path
from types         import ModuleType
from typing        import cast
from core.oracle   import Oracle
from core.config   import Config
from core.errors   import ConfigError
from loader.family import Family, Case, OracleFactory


_MANIFEST = "manifest.json"


# imported plugin modules, keyed by source path - a plugin is executed at most once
_modules:dict[Path, ModuleType] = {}


def _build_command(family_dir:Path, data:dict) -> str | None:
	"""The family's build command, runnable from the caller's working directory.

	A manifest declares only *what* to run, since where to run it is its own
	directory - which it cannot name without hardcoding where it happens to sit.
	The location is supplied here, so a family loaded from anywhere reports a
	command that works.
	"""

	build = data.get("build")

	if build is None: return None

	try:               where = family_dir.relative_to(Path.cwd())
	except ValueError: where = family_dir

	return f"cd {where} && {build}"


def _read_manifest(family_dir:Path) -> Config:
	"""Parse a family's manifest."""

	path = family_dir / _MANIFEST

	if not path.is_file(): raise ConfigError(f"no {_MANIFEST} found at {family_dir}")

	try:                              data = json.loads(path.read_text())
	except json.JSONDecodeError as e: raise ConfigError(f"{path}: invalid JSON ({e})") from e

	if not isinstance(data, dict):
		raise ConfigError(f"{path}: expected a top-level JSON object")

	return Config(data, where=str(path))


def _within(family_dir:Path, rel:str, at:str) -> Path:
	"""Resolve a family-relative path, and refuse one that leaves the family.

	Every path a manifest declares belongs to its own family - that is what
	makes a family self-contained and relocatable. A `..` that climbs out is a
	typo, and an expensive one: the escaped path usually still exists, so the
	case would run happily against the wrong file and report a plausible number.
	"""

	if Path(rel).is_absolute(): raise ConfigError(f"{at}: {rel!r} must be relative to the family")

	resolved = (family_dir / rel).resolve()

	if not resolved.is_relative_to(family_dir.resolve()):
		raise ConfigError(f"{at}: {rel!r} escapes the family directory")

	return family_dir / rel


def _load_cases(family_dir:Path, data:Config, build:str | None) -> dict[str, Case]:
	"""Build the Cases from a parsed manifest, keyed by id.

	A predicate entry is `id`, `path` (its input, relative to the family), and
	the functional and human halves of the rest:

	    config  the oracle's settings - manifest `common` overlaid with the
	            case's own, plus the family `build` so an oracle can name it when
	            an artifact is absent
	    files   auxiliary family-relative paths the oracle needs, resolved here
	            into config under their own names
	    meta    provenance the loader carries but never reads (a url, a summary)
	"""

	where  = family_dir / _MANIFEST
	common = data.get("common", {})
	result = {}

	for i, entry in enumerate(data["predicates"]):

		at = f"{where}: predicate {i}"

		if not isinstance(entry, dict): raise ConfigError(f"{at}: expected an object")

		p  = Config(entry, where=at)
		id = p["id"]

		# ids key the family, so a duplicate would silently drop a case
		if id in result: raise ConfigError(f"{at}: duplicate case id {id!r}")

		# concatenate common and individual config, tagged with the case it is for
		config = Config({**common, **p.get("config", {})}, where=f"{at} ({id!r})")

		# the family's build reaches every case
		if build is not None: config["build"] = build

		# resolve any auxiliary files the case declares
		for name, rel in p.get("files", {}).items():

			# a collision would silently shadow a config value with a path
			if name in config: raise ConfigError(f"{at}: {name!r} is both a config key and a file")

			config[name] = _within(family_dir, rel, f"{at}: files.{name}")

		result[id] = Case(id, _within(family_dir, p["path"], f"{at}: path"), config, p.get("meta", {}))

	return result


def _import_plugin(source:Path, family_dir:Path) -> ModuleType:
	"""Import `source` as a throwaway package rooted at its family directory.

	The package is what makes an oracle's own `from .basex import ...` resolve
	against its family's files.
	"""

	if source in _modules: return _modules[source]

	pkg  = f"dd_predicate_{family_dir.name}"
	spec = importlib.util.spec_from_file_location(

		name                       = pkg,
		location                   = source,
		submodule_search_locations = [str(family_dir)],

	)

	if not (spec and spec.loader): raise ConfigError(f"{source} is not importable")

	# register before exec so relative imports resolve
	module           = importlib.util.module_from_spec(spec)
	sys.modules[pkg] = module

	try: spec.loader.exec_module(module)

	except Exception as e:
		# don't leave a half-initialized module registered
		sys.modules.pop(pkg, None)

		raise ConfigError(f"{source}: import failed ({type(e).__name__}: {e})") from e

	_modules[source] = module

	return module


def _load_oracle(family_dir:Path, ref:str) -> OracleFactory:
	"""Resolve the Oracle class a manifest names.

	`ref` is `<module>:<class>`, the module relative to the family directory:

	    "oracle": "oracle.py:CrashJSOracle"

	Nothing is guessed from the layout - the class is named and looked up, rather
	than the module being imported and searched for whatever happens to subclass
	Oracle. A family may then keep as many classes as it likes.
	"""

	where          = family_dir / _MANIFEST
	rel, sep, name = ref.partition(":")

	if not (sep and rel and name):
		raise ConfigError(f"{where}: oracle must be '<module>:<class>', got {ref!r}")

	source = (family_dir / rel).resolve()

	if not source.is_file(): raise ConfigError(f"{where}: no {rel} in {family_dir}")

	obj = getattr(_import_plugin(source, family_dir), name, None)

	if obj is None:
		raise ConfigError(f"{where}: {source} defines no {name!r}")

	if not (isinstance(obj, type) and issubclass(obj, Oracle)):
		raise ConfigError(f"{where}: {name!r} in {source} is not an Oracle subclass")

	return cast(OracleFactory, obj)


def load_family(family_dir:Path) -> Family:
	"""Resolve a predicate family's directory into a Family."""

	data  = _read_manifest(family_dir)
	build = _build_command(family_dir, data)

	return Family(

		name   = data["name"],
		oracle = _load_oracle(family_dir, data["oracle"]),
		build  = build,
		cases  = _load_cases(family_dir, data, build),
		tuning = data.get("tuning", {}),

	)

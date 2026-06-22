from pathlib     import Path
from core.errors import ConfigError


class Config(dict):
	"""A resolved predicate config. - a missing key is a ConfigError."""

	def __missing__(self, key):
		raise ConfigError(f"missing config key: {key!r}")


def require(path:Path, hint:str | None = None) -> Path:
	"""Return `path`, or a ConfigError (with a build hint) if it isn't present."""

	if path.exists(): return path

	raise ConfigError(f"{path} not found" + (f" (build it with: {hint})" if hint else ""))

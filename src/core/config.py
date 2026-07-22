from pathlib     import Path
from core.errors import ConfigError


class Config(dict):
	"""Keyed data that reports its origin, with reportable errors.

	Manifests are hand-edited, so a missing key is a routine authoring mistake
	rather than a bug. `where` is what makes the resulting error actionable: it
	names the file and the entry the key was expected in, so the reader is not
	left to guess which of a family's cases is malformed.
	"""

	def __init__(self, data:dict, where:str) -> None:
		super().__init__(data)

		self._where = where


	def __missing__(self, key):
		raise ConfigError(f"{self._where}: missing {key!r}")


def require(path:Path, build:str | None = None) -> Path:
	"""Return `path`, or a ConfigError naming the command that would produce it.

	`is_file`, not `exists`: every caller wants a built artifact, and a directory
	sitting at that path would otherwise pass and fail later, further from the
	cause.
	"""

	if path.is_file(): return path

	raise ConfigError(f"{path} not found" + (f" (build it with: {build})" if build else ""))

class DDError(Exception):
	"""Base for anticipated, user-facing errors (raised via a subclass)."""


class ConfigError(DDError):
	"""Invalid or missing predicate config, manifest, input, or build artifact."""


class OracleError(DDError):
	"""A predicate's oracle failed operationally (server, subprocess, worker)."""

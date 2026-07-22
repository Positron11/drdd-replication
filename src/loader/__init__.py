"""The predicate pool: families of cases, and how to load them.

A predicate family is a directory holding a `manifest.json`. The manifest is the
source of truth - it names the family, the Oracle class that implements its
predicate, and the cases that exercise it. `load_family` resolves one into a
`Family`; nothing else in the library names a family.
"""

from loader.family import Family, Case, OracleFactory
from loader.plugin import load_family


__all__ = ["Family", "Case", "OracleFactory", "load_family"]

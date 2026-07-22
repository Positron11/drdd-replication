"""Shared helpers for the benchmark's experiment scripts.

Scripts are run as `python benchmark/scripts/<x>.py`, so their own directory is
on sys.path and `from _common import ...` resolves.
"""

import sys

from pathlib       import Path
from core.errors   import DDError
from loader        import load_family, Family, Case
from reducers      import tuning_for
from reducers.drdd import causal_chain_scan


# the predicate families live at the repo root, read as data (never imported)
ROOT       = Path(__file__).resolve().parents[2]
PREDICATES = ROOT / "predicates"
RUNS       = ROOT / "benchmark" / "runs"


def entry(fam:str, cid:str) -> tuple[Family, Case]:
	"""Resolve one case to its (family, case), or abort."""

	family = load_family(PREDICATES / fam)

	try: case = family.case(cid)
	except DDError as e: sys.exit(f"  {e}")

	return family, case


def verify_minimal(family:Family, case:Case, output:bytes) -> tuple[int, int]:
	"""The 1-minimal residue of `output`, and the oracle calls it took to find.

	This is the operational definition of 1-minimality used throughout the
	paper: run drdd's single-element scan to its fixed point and see whether
	anything still comes off. A fresh oracle keeps these verification calls out
	of whatever cost the caller is measuring.
	"""

	oracle = family.oracle(case.config)

	with oracle:
		minimal = causal_chain_scan(output, oracle)

	return len(minimal), oracle.calls


__all__ = ["ROOT", "PREDICATES", "RUNS", "entry", "verify_minimal", "tuning_for"]

#!/usr/bin/env python3
"""R-ablation study of drdd: efficiency / quality / minimality vs restart budget.

drdd exposes a restart budget R (its `c_iters`) controlling how many
single-element fixed-point scans it runs at the finest granularity:

    R = |I|  fully resolves causal chains -> 1-minimal, most oracle calls
    R = 1    one linear pass, no causal resolution, no 1-minimality guarantee
    1<R<|I|  interpolates

For each (subject, R) the study records the three tradeoff axes:

    1. oracle calls   - the primary cost metric
    2. output size    - reduction quality
    3. 1-minimality   - shortfall = how many single elements are still
                        removable, found by driving drdd's own causal-chain
                        scan to a fixed point on the output (a fixed point of
                        the size-1 sweep is, by definition, 1-minimal). A
                        fresh oracle keeps verification calls out of the cost.

Re-runnable: writes a timestamped run dir under benchmark/runs/ holding the
per-subject table plus per-family and per-R aggregates, ready for plotting.
Expand the study by editing R_VALUES and SUBJECTS below.
"""

import sys
import time

from pathlib        import Path
from core.errors    import DDError
from reducers       import REDUCERS
from reducers.drdd  import _causal_chain_scan
from loader         import load_dataset, Family, Case
from runtime.runner import run_minimization
from bench.results  import result_dir, write_csv

# the predicate datasets live at the repo root, read as data (never imported)
_ROOT       = Path(__file__).resolve().parents[2]
_PREDICATES = _ROOT / "predicates"


# study configuration (expand here)

# restart budgets to sweep. None = |I| (full budget; resolves causal chains to
# a fixed point and so is guaranteed 1-minimal).
R_VALUES = [1, 2, 4, 8, None]

# subjects per family, chosen to span the reducibility spectrum at a feasible
# wall-clock cost. add families/cases freely — ids match the family manifest.
SUBJECTS = {
	"binutils": ["21414", "21135", "21409-2", "21136"],
	"crashjs" : ["9", "6", "1", "3", "5"],
	"ffmpeg"  : ["10686", "10702", "10744"],
	"xml"     : ["1.1", "3.1", "1.2"],
}

_REDUCER = "drdd"
_RUNS    = _ROOT / "benchmark" / "runs"

# nominal budget labels, in plotting order
_FULL  = "|I|"
_ORDER = {"1": 0, "2": 1, "4": 2, "8": 3, _FULL: 4}


def _label(R:int | None) -> str:
	"""Nominal label for a budget: integers as-is, the full budget as '|I|'."""

	return _FULL if R is None else str(R)


def _budgets(size:int) -> list[tuple[str, int]]:
	"""Resolve R_VALUES against an input of `size`, de-duping coincident budgets."""

	seen     = set()
	resolved = []

	for R in R_VALUES:
		iters = size if R is None else R

		if iters in seen: continue

		seen.add(iters)
		resolved.append((_label(R), iters))

	return resolved


def _measure(family:Family, case:Case, data:bytes, iters:int) -> tuple[bytes, int, float]:
	"""One reduction at budget `iters`; return (output, oracle_calls, wall_s)."""

	oracle = family.oracle(case.config)

	start = time.perf_counter()
	out   = run_minimization(data, REDUCERS[_REDUCER], oracle, c_iters=iters)
	wall  = time.perf_counter() - start

	return out, oracle.calls, wall


def _verify_minimal(family:Family, case:Case, output:bytes) -> tuple[int, int]:
	"""1-minimal residue of `output`, via drdd's single-element fixed-point scan.

	A fresh oracle keeps these verification calls out of the cost metric.
	"""

	oracle = family.oracle(case.config)

	with oracle:
		minimal = _causal_chain_scan(list(output), len(output), oracle)

	return len(minimal), oracle.calls


def _aggregate(rows:list[dict], keys:tuple[str, ...]) -> list[dict]:
	"""Mean cost/quality/minimality grouped by `keys`, in budget order."""

	groups:dict = {}

	for r in rows:
		if r.get("error"): continue

		groups.setdefault(tuple(r[k] for k in keys), []).append(r)

	out = []

	for key, rs in groups.items():
		n   = len(rs)
		agg = dict(zip(keys, key))

		agg["n"]                 = n
		agg["mean_calls"]        = round(sum(x["oracle_calls"]  for x in rs) / n, 1)
		agg["mean_output_bytes"] = round(sum(x["output_bytes"]  for x in rs) / n, 1)
		agg["mean_shortfall"]    = round(sum(x["shortfall"]     for x in rs) / n, 2)
		agg["frac_1_minimal"]    = round(sum(x["is_1_minimal"]  for x in rs) / n, 3)
		agg["mean_wall_s"]       = round(sum(x["wall_s"]        for x in rs) / n, 2)

		out.append(agg)

	return sorted(out, key=lambda a: (a.get("family", ""), _ORDER[a["R"]]))


def _write(rows:list[dict], run_dir:Path) -> None:
	"""Persist the per-subject table and the per-family / per-R aggregates."""

	if not rows: print("No results to write."); return

	write_csv(rows,                              run_dir / "results.csv")
	write_csv(_aggregate(rows, ("family", "R")), run_dir / "by_family.csv")
	write_csv(_aggregate(rows, ("R",)),          run_dir / "by_R.csv")

	# terminal summary: the cost/minimality curve across R
	print(f"\nper-R summary (all families):\n")
	print(f"  {'R':>4}  {'mean_calls':>11}  {'mean_out_B':>11}  {'mean_short':>11}  {'1-min frac':>11}")

	for a in _aggregate(rows, ("R",)):
		print(f"  {a['R']:>4}  {a['mean_calls']:>11}  {a['mean_output_bytes']:>11}  {a['mean_shortfall']:>11}  {a['frac_1_minimal']:>11}")

	print(f"\nwrote {len(rows)} rows -> {run_dir}\n")


def main() -> None:
	run_dir  = _RUNS / result_dir("drdd_ablation")
	subjects = [(fam, cid) for fam, ids in SUBJECTS.items() for cid in ids]
	total    = sum(len(_budgets(_size(fam, cid))) for fam, cid in subjects)
	rows     = []
	i        = 0

	print(

		f"\ndrdd R-ablation\n\n"
		f"subjects : {len(subjects)}\n"
		f"budgets  : {', '.join(_label(R) for R in R_VALUES)}\n"
		f"reducer  : {_REDUCER}\n"
		f"output   : {run_dir}\n"

	)

	try:
		for fam, cid in subjects:
			family, case = _entry(fam, cid)
			data         = case.path.read_bytes()

			for label, iters in _budgets(len(data)):
				i += 1
				print(f"  {i:>3}/{total}  {fam}/{cid:<10} R={label:<3} ...", flush=True)

				try:
					out, calls, wall = _measure(family, case, data, iters)
					minimal, vcalls  = _verify_minimal(family, case, out)

				except DDError as e:
					rows.append({"family": fam, "subject": cid, "R": label, "error": str(e)})
					print(f"          error: {e}")

					continue

				shortfall = len(out) - minimal

				rows.append({

					"family"       : fam,
					"subject"      : cid,
					"input_bytes"  : len(data),
					"R"            : label,
					"R_iters"      : iters,
					"oracle_calls" : calls,
					"output_bytes" : len(out),
					"minimal_bytes": minimal,
					"shortfall"    : shortfall,
					"is_1_minimal" : int(shortfall == 0),
					"verify_calls" : vcalls,
					"wall_s"       : round(wall, 2),

				})

				flag = "1-min" if shortfall == 0 else f"NOT 1-min (+{shortfall})"
				print(f"          calls={calls:<7} out={len(out)}B  {flag}  {wall:.1f}s")

	except KeyboardInterrupt:
		print("\nInterrupted - writing partial results.\n")

	_write(rows, run_dir)


def _entry(fam:str, cid:str) -> tuple[Family, Case]:
	"""Resolve one case to its (family, case), or abort."""

	family = load_dataset(_PREDICATES / fam)

	try: case = family.case(cid)
	except DDError as e: sys.exit(f"  {e}")

	return family, case


def _size(fam:str, cid:str) -> int:
	"""Input size of one case (for the progress denominator)."""

	return _entry(fam, cid)[1].path.stat().st_size


if __name__ == "__main__":
	main()

#!/usr/bin/env python3
"""Non-1-minimality verification of ProbDD and CDD.

The paper claims ProbDD and CDD stop short of 1-minimality, unlike drdd. This
tests it directly: for each subject, regenerate the competitor's reduced output
and then run the single-element fixed-point reducer — the same verifier used by
the R-ablation (drdd's `_causal_chain_scan`) — against the subject's own oracle.
Any element it removes is one the competitor left behind, so the output was not
1-minimal; the bytes removed quantify the shortfall.

The competitor outputs are not persisted in prior runs (only sizes/calls are),
so they are regenerated here. Both algorithms are reproducible: CDD is
deterministic and ProbDD is seeded, so a regenerated output matches the original
run. drdd's 1-minimal output is the reference — a faithful verification reduces
each competitor output to at or near that size.

What we record per (subject, algorithm):

    1. start_bytes   - the competitor's reduced output (the starting point)
    2. reduced_bytes - after the single-element fixed-point pass
    3. shortfall     - start_bytes - reduced_bytes (0 iff already 1-minimal)
    4. verify_calls  - oracle calls used by the verification (secondary)

Re-runnable: writes a timestamped run dir under benchmark/runs/ with the
per-subject table plus per-family and per-algorithm aggregates. Expand the study
by editing ALGORITHMS and SUBJECTS below.
"""

import sys
import time

from pathlib import Path

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

# competitors to verify. both consume p_0 from the manifest; ProbDD is seeded.
ALGORITHMS = ["probdd", "cdd"]

# subjects per family — mirrors the R-ablation set for cross-experiment
# comparability. ids match the family manifest.
SUBJECTS = {
	"binutils": ["21414", "21135", "21409-2", "21136"],
	"crashjs" : ["9", "6", "1", "3", "5"],
	"ffmpeg"  : ["10686", "10702", "10744"],
	"xml"     : ["1.1", "3.1", "1.2"],
}

# drdd's 1-minimal output size (from the R-ablation / paper Table I), for context
# only: a faithful verification lands reduced_bytes at or near this. Frozen snapshot
# - refresh these if drdd's output changes; nothing in the study logic depends on it.
REFERENCE = {
	"binutils/21414": 680,  "binutils/21135": 640, "binutils/21409-2": 1422, "binutils/21136": 3944,
	"crashjs/9": 217, "crashjs/6": 176, "crashjs/1": 542, "crashjs/3": 747, "crashjs/5": 1298,
	"ffmpeg/10686": 17, "ffmpeg/10702": 94, "ffmpeg/10744": 643,
	"xml/1.1": 401, "xml/3.1": 634, "xml/1.2": 1151,
}

_RUNS = _ROOT / "benchmark" / "runs"


def _generate(family:Family, case:Case, data:bytes, algo:str) -> tuple[bytes, int]:
	"""Reproduce a competitor's reduced output; return (output, oracle_calls)."""

	oracle = family.oracle(case.config)
	kwargs = {"p_0": family.tuning["p_0"]} if "p_0" in family.tuning else {}
	out    = run_minimization(data, REDUCERS[algo], oracle, **kwargs)

	return out, oracle.calls


def _verify_minimal(family:Family, case:Case, output:bytes) -> tuple[int, int]:
	"""1-minimal residue of `output` via drdd's single-element fixed-point scan.

	A fresh oracle keeps these verification calls out of the competitor's cost.
	"""

	oracle = family.oracle(case.config)

	with oracle:
		minimal = _causal_chain_scan(list(output), len(output), oracle)

	return len(minimal), oracle.calls


def _aggregate(rows:list[dict], keys:tuple[str, ...]) -> list[dict]:
	"""Mean start/reduced/shortfall and already-1-minimal fraction by `keys`."""

	groups:dict = {}

	for r in rows:
		if r.get("error"): continue

		groups.setdefault(tuple(r[k] for k in keys), []).append(r)

	out = []

	for key, rs in groups.items():
		n   = len(rs)
		agg = dict(zip(keys, key))

		agg["n"]                  = n
		agg["mean_start_bytes"]   = round(sum(x["start_bytes"]   for x in rs) / n, 1)
		agg["mean_reduced_bytes"] = round(sum(x["reduced_bytes"] for x in rs) / n, 1)
		agg["mean_shortfall"]     = round(sum(x["shortfall"]     for x in rs) / n, 2)
		agg["frac_1_minimal"]     = round(sum(x["is_1_minimal"]  for x in rs) / n, 3)
		agg["mean_verify_calls"]  = round(sum(x["verify_calls"]  for x in rs) / n, 1)

		out.append(agg)

	order = {a: i for i, a in enumerate(ALGORITHMS)}

	return sorted(out, key=lambda a: (a.get("family", ""), order.get(a["algorithm"], 0)))


def _write(rows:list[dict], run_dir:Path) -> None:
	"""Persist the per-subject table and the per-family / per-algorithm aggregates."""

	if not rows: print("No results to write."); return

	write_csv(rows,                                     run_dir / "results.csv")
	write_csv(_aggregate(rows, ("family", "algorithm")), run_dir / "by_family.csv")
	write_csv(_aggregate(rows, ("algorithm",)),          run_dir / "by_algorithm.csv")

	# terminal summary: the headline non-1-minimality signal per algorithm
	print(f"\nper-algorithm summary (all families):\n")
	print(f"  {'algo':>8}  {'mean_start':>11}  {'mean_reduced':>13}  {'mean_short':>11}  {'1-min frac':>11}")

	for a in _aggregate(rows, ("algorithm",)):
		print(f"  {a['algorithm']:>8}  {a['mean_start_bytes']:>11}  {a['mean_reduced_bytes']:>13}  {a['mean_shortfall']:>11}  {a['frac_1_minimal']:>11}")

	print(f"\nwrote {len(rows)} rows -> {run_dir}\n")


def main() -> None:
	run_dir  = _RUNS / result_dir("competitor_minimality")
	subjects = [(fam, cid) for fam, ids in SUBJECTS.items() for cid in ids]
	total    = len(subjects) * len(ALGORITHMS)
	rows     = []
	i        = 0

	print(

		f"\nProbDD/CDD non-1-minimality verification\n\n"
		f"subjects   : {len(subjects)}\n"
		f"algorithms : {', '.join(ALGORITHMS)}\n"
		f"output     : {run_dir}\n"

	)

	try:
		for fam, cid in subjects:
			family, case = _entry(fam, cid)
			data         = case.path.read_bytes()
			ref          = REFERENCE.get(f"{fam}/{cid}")

			for algo in ALGORITHMS:
				i += 1
				print(f"  {i:>3}/{total}  {algo:<7} {fam}/{cid:<10} ...", flush=True)

				start = time.perf_counter()

				try:
					output, gen_calls    = _generate(family, case, data, algo)
					reduced, verify_calls = _verify_minimal(family, case, output)

				except DDError as e:
					rows.append({"family": fam, "subject": cid, "algorithm": algo, "error": str(e)})
					print(f"          error: {e}")

					continue

				wall      = time.perf_counter() - start
				shortfall = len(output) - reduced

				rows.append({

					"family"       : fam,
					"subject"      : cid,
					"algorithm"    : algo,
					"input_bytes"  : len(data),
					"start_bytes"  : len(output),
					"reduced_bytes": reduced,
					"shortfall"    : shortfall,
					"is_1_minimal" : int(shortfall == 0),
					"drdd_ref"     : ref if ref is not None else "",
					"gap_to_ref"   : reduced - ref if ref is not None else "",
					"verify_calls" : verify_calls,
					"gen_calls"    : gen_calls,
					"wall_s"       : round(wall, 2),

				})

				flag = "1-min" if shortfall == 0 else f"NOT 1-min (-{shortfall})"
				print(f"          start={len(output)}B -> {reduced}B  {flag}  (drdd ref {ref})  {wall:.1f}s")

	except KeyboardInterrupt:
		print("\nInterrupted - writing partial results.\n")

	_write(rows, run_dir)


def _entry(fam:str, cid:str) -> tuple[Family, Case]:
	"""Resolve one case to its (family, case), or abort."""

	family = load_dataset(_PREDICATES / fam)

	try: case = family.case(cid)
	except DDError as e: sys.exit(f"  {e}")

	return family, case


if __name__ == "__main__":
	main()

#!/usr/bin/env python3
"""Reproduce the paper's main benchmark table (Dr. DD, ISSRE 2026).

Runs the four reported reducers against every case of all four predicate families
and writes one timestamped run dir per family under benchmark/runs/ — the same
harness and output format that produced the paper's numbers. This is the main
Table II reproduction; the two supplementary studies live alongside it in
ablate_drdd.py (drdd's R-ablation) and verify_competitors.py (ProbDD/CDD
non-1-minimality).

Reducers, in table order:

    ddmin   classic Delta Debugging baseline      (deterministic)
    probdd  ProbDD competitor                     (stochastic -> counts vary slightly per run)
    cdd     CDD competitor                        (deterministic; consumes p_0 from the manifest)
    drdd    Dr. DD, this paper                     (deterministic)

The deterministic reducers reproduce the archived runs to the exact
(length, oracle-call) pair; ProbDD lands close but not identical, as it is
stochastic by nature.

Prerequisites — each family's oracle lib must be built (see benchmark/README.md):

    make -C predicates/ffmpeg     # clang
    make -C predicates/binutils   # flex/bison/m4
    make -C predicates/crashjs    # + node

A family whose lib is missing is reported and skipped so the rest still run.
"""

import sys

from pathlib       import Path
from bench.harness import run_family_benchmark
from bench.results import result_dir

# the predicate datasets live at the repo root, read as data (never imported)
_ROOT       = Path(__file__).resolve().parents[2]
_PREDICATES = _ROOT / "predicates"
_RUNS       = _ROOT / "benchmark" / "runs"


# the four reducers the paper reports, in table order
PAPER_REDUCERS = ["ddmin", "probdd", "cdd", "drdd"]

# every family; [] selects all cases of each from its manifest.json
FAMILIES = ["binutils", "crashjs", "ffmpeg", "xml"]


def main() -> None:
	print(

		f"\nDr. DD — ISSRE 2026 benchmark reproduction\n\n"
		f"families : {', '.join(FAMILIES)}\n"
		f"reducers : {', '.join(PAPER_REDUCERS)}\n"
		f"output   : {_RUNS}\n"

	)

	done, skipped = [], []

	for name in FAMILIES:
		run_dir = _RUNS / result_dir(name)

		# run_family_benchmark exits (SystemExit) on a setup failure — e.g. an
		# unbuilt lib — having already printed the reason; catch it so one missing
		# family doesn't sink the rest of the reproduction.
		try:
			run_family_benchmark(_PREDICATES, name, PAPER_REDUCERS, [], run_dir)
			done.append(name)

		except SystemExit:
			skipped.append(name)
			print(f"  -> {name} skipped (build its lib, then re-run)\n", file=sys.stderr)

		except KeyboardInterrupt:
			print("\nInterrupted.\n")
			break

	print(f"\nreproduced : {', '.join(done) or 'none'}")
	if skipped: print(f"skipped    : {', '.join(skipped)}")
	print()


if __name__ == "__main__":
	main()

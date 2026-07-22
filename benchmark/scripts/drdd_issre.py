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
    probdd  ProbDD competitor                     (probabilistic; seeded at 0, so
                                                   it re-runs identically on a host)
    cdd     CDD competitor                        (deterministic; consumes p_0 from the manifest)
    drdd    Dr. DD, this paper                     (deterministic)

ddmin, cdd and drdd reproduce the reported (length, oracle-call) pairs exactly.
ProbDD's seed is fixed, so re-running it on one host gives identical counts; only
across hosts can NumPy RNG and floating-point differences move them. See the
*Reproduction caveats* in the root README for that and for the one
ASLR-sensitive binutils case.

Prerequisites — each family's oracle lib must be built (see benchmark/README.md):

    make -C predicates/ffmpeg     # clang
    make -C predicates/binutils   # flex/bison/m4
    make -C predicates/crashjs    # + node

A family whose lib is missing is reported and skipped so the rest still run.
"""

import sys

from bench.harness import run_family_benchmark
from bench.results import result_dir

from _common import PREDICATES, RUNS


# the four reducers the paper reports, in table order
PAPER_REDUCERS = ["ddmin", "probdd", "cdd", "drdd"]

# the paper's four subject families; [] selects all cases of each from its
# manifest.json
FAMILIES = ["binutils", "crashjs", "ffmpeg", "xml"]


def main() -> None:
	print(

		f"\nDr. DD — ISSRE 2026 benchmark reproduction\n\n"
		f"families : {', '.join(FAMILIES)}\n"
		f"reducers : {', '.join(PAPER_REDUCERS)}\n"
		f"output   : {RUNS}\n"

	)

	done, skipped = [], []

	for name in FAMILIES:
		run_dir = RUNS / result_dir(name)

		# run_family_benchmark exits (SystemExit) on a setup failure — e.g. an
		# unbuilt lib — having already printed the reason; catch it so one missing
		# family doesn't sink the rest of the reproduction.
		try:
			run_family_benchmark(PREDICATES, name, PAPER_REDUCERS, [], run_dir)
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

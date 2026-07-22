# Status

Badges claimed for this artifact, under the
[ACM Artifact Review and Badging policy (current)](https://www.acm.org/publications/policies/artifact-review-and-badging-current).

## Artifacts Available

The package is archived with a DOI (see *Data Availability* in the paper) and is
self-contained: every reducer implementation, every predicate input, every build
recipe, and a container definition that freezes the whole environment. It is
released under the MIT License ([`LICENSE`](LICENSE)).

Predicate subjects derive from public datasets and bug trackers and are cited per
family in [`predicates/README.md`](predicates/README.md); their provenance is
recorded in each family's `manifest.json`.

## Artifacts Evaluated — Functional

Everything documented is runnable as documented, and the package can demonstrate
this about itself:

- Every reduction is self-verifying: the runner re-checks (uncounted) that the
  minimized output still reproduces the predicate before returning it, so a
  reducer cannot silently report a result that does not hold.
- Malformed input is diagnosed, not crashed on: every way a hand-edited
  `manifest.json` can be wrong is reported as a `ConfigError` naming the file and
  the offending entry.
- [`INSTALL.md`](INSTALL.md) gives the install and a basic functionality check;
  [`REQUIREMENTS.md`](REQUIREMENTS.md) gives what each family needs, so a
  reviewer can run a subset without the full toolchain — XML needs no build at
  all.

## Artifacts Evaluated — Reusable

The library is family-agnostic: every reducer treats its input as an opaque byte
sequence and learns nothing about the format, and nothing under
[`src/`](src/) names a predicate family.

A family is a directory with a `manifest.json`, which is the contract — it names
the family, the `Oracle` class implementing its predicate, its build command, and
its cases. **Adding a case or an entire new family requires no change under
`src/`.** The contract is specified in
[`predicates/README.md`](predicates/README.md).

## Results Reproduced

[`benchmark/scripts/drdd_issre.py`](benchmark/scripts/drdd_issre.py) regenerates
the per-case minimized length and oracle-call counts of the paper's main table;
[`ablate_drdd.py`](benchmark/scripts/ablate_drdd.py) and
[`verify_competitors.py`](benchmark/scripts/verify_competitors.py) regenerate the
restart-budget and lost-minimality tables.

`ddmin`, `cdd` and `drdd` are deterministic and reproduce their reported
`(minimized_length, oracle_invocations)` pairs exactly. Two narrow exceptions,
neither affecting any conclusion, are documented under *Reproduction caveats* in
the [README](README.md): ProbDD is seeded and so reproduces on a given host but
is only platform-stable insofar as the NumPy RNG agrees, and one binutils case
(`21409-2`) is address-space-layout sensitive.

Every `result.csv` records the `input_sha256` of each subject alongside its
metrics, so a reproduction attempt carries proof of which inputs produced it.

**Cost.** A full four-family reproduction takes ~11 hours on the reference setup;
per-family and per-case subsets are available via `cli/bench` for spot-checking.
See [`REQUIREMENTS.md`](REQUIREMENTS.md).

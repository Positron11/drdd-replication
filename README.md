# Dr. DD — Replication Package (ISSRE 2026, Paper 238)

Replication package for "Dr. DD: 1-Minimal Isolation of Failure Causes via Deferred Restarts." It contains the four Delta Debugging reducers the paper evaluates, the four predicate (bug-reproducer) families used as subjects, and the scripts that regenerate the paper's tables. Every reducer treats its input as an opaque byte sequence.

`drdd` matches `ddmin`'s reduction quality using far fewer oracle calls (1.7% on XML, 50% on FFmpeg), and unlike ProbDD and CDD it preserves 1-minimality.

The artifact document is [`README.txt`](README.txt); it follows the eight-section ISSRE structure and is self-contained. [`REQUIREMENTS.md`](REQUIREMENTS.md) and [`INSTALL.md`](INSTALL.md) cover prerequisites and setup.

## Reducers

Four reducers under [`src/reducers/`](src/reducers/), one per algorithm the paper evaluates.

| Reducer | Paper ref. | Strategy | Literature |
|---------|------------|----------|------------|
| [`ddmin`](src/reducers/ddmin.py)  | `ddmin`$^Y$ | Classical halving complement sweep with restart-after-success | Zeller & Hildebrandt |
| [`drdd`](src/reducers/drdd.py)    | **Dr. DD** | Halving complement sweep + deferred single-element causal-chain scan | — |
| [`probdd`](src/reducers/probdd.py)| ProbDD | Per-element removal probabilities, updated on each rejection | [Wang et al.](https://doi.org/10.1145/3468264.3468625) |
| [`cdd`](src/reducers/cdd.py)      | CDD | Deterministic counter-driven partition schedule (no restarts) | [Zhang et al.](https://doi.org/10.1109/ICSE55347.2025.00117) |

The paper writes the simplified classical baseline as `ddmin`$^Y$ (the *Why Programs Fail* / Fuzzingbook form); this code calls it `ddmin`. The contribution, `drdd`, is "Dr. DD".

## Predicates

Four families, each a self-contained plugin under [`predicates/`](predicates/). Inputs ship in-tree; oracle binaries are built from pinned upstream source by each family's `Makefile`, or baked into the container. Build and provenance detail per family is in [`predicates/README.md`](predicates/README.md).

| Family | Cases | Bug type |
|--------|-------|----------|
| [XML](predicates/xml/) | 5 cases × 3 size variants | XQuery output discrepancy between two BaseX versions |
| [FFmpeg](predicates/ffmpeg/) | 14 cases | AddressSanitizer report under a specific filter |
| [Binutils](predicates/binutils/) | 12 cases | SIGSEGV / glibc heap corruption in `readelf`, `objdump`, `objcopy`, `nm` |
| [CrashJS](predicates/crashjs/) | 11 cases | `TypeError` in an instrumented `lodash` build |

## Repository layout

| Path | Contents | Detail |
|------|----------|--------|
| [`src/`](src/) | The installable library: reducers, the oracle and family contracts, the plugin loader, the runner, the benchmark harness. | — |
| [`predicates/`](predicates/) | The four subject families: each a `manifest.json`, an `oracle.py`, its input `cases/`, and a `Makefile` where a build is needed. | [`predicates/README.md`](predicates/README.md) |
| [`cli/`](cli/) | `minimize` (one case, one reducer) and `bench` (a spec-selected matrix). | [`cli/README.md`](cli/README.md) |
| [`benchmark/`](benchmark/) | The experiment scripts, the reproduction specs, and the `runs/` output. | [`benchmark/README.md`](benchmark/README.md) |
| [`Dockerfile`](Dockerfile) | Reproduction image with all four oracles built in. | [`README.txt`](README.txt) §7 |
| [`Makefile`](Makefile) | `make dist`, `make clean`; `make help` lists them. | — |

## Quick start

The XML family needs only a JRE (its BaseX jars ship in-tree), so this runs with no oracle build, in about 70 seconds:

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -e .
cli/bench benchmark/specs/getting-started.json
```

The `result.csv` reproduces row T-1e9bc83-1-1 of Table II: `ddmin` 396 B / 32,567 calls, `drdd` 401 B / 1,618 calls. Setup and the tiered reproduction (≈70 s / ≈2.2 h / ≈10 h) are in [`README.txt`](README.txt) §7–§8.

## Reproducing the paper

Full guide: [`README.txt`](README.txt) §8. Build the oracle libs you need (`make -C predicates/<family>`), then:

```bash
cli/bench benchmark/specs/reduced.json      # all 4 families × 4 reducers, ~2.2 h
python benchmark/scripts/drdd_issre.py      # complete ~10 h main table
```

The three scripts in [`benchmark/scripts/`](benchmark/scripts/) regenerate the paper's tables: `drdd_issre.py` (main table), `ablate_drdd.py` (Table V), `verify_competitors.py` (Table IV); see [`benchmark/README.md`](benchmark/README.md). The deterministic reducers reproduce their `(size, oracle-call)` pairs exactly. Two exceptions — ProbDD's seed sensitivity and the ASLR-sensitive binutils `21409-2` — are covered in [`README.txt`](README.txt) §8.

## Extending it

The loader reads any directory under `predicates/` that holds a `manifest.json`, so a new case or family needs no change under `src/`. The contract is in [`predicates/README.md`](predicates/README.md).

## Artifact evaluation

Targets the Reproducible badge (ISSRE hierarchy: Reproducible ⊃ Reviewed ⊃ Available). Archived at [`10.5281/zenodo.21498483`](https://doi.org/10.5281/zenodo.21498483) under the MIT [`LICENSE`](LICENSE). Details in [`README.txt`](README.txt) §2.

## Provenance and license

Predicate subjects come from public datasets and bug trackers: XML from Zhang et al.'s artifact, FFmpeg from trac tickets at pinned commits, binutils from sourceware Bugzilla, CrashJS from Zenodo record 10530515. They are cited per family in [`predicates/README.md`](predicates/README.md). MIT License; see [`LICENSE`](LICENSE).

# Dr. DD — Replication Package (ISSRE 2026, Paper 238)

Replication package for **"Dr. DD: 1-Minimal Isolation of Failure Causes via Deferred Restarts."** It contains every Delta Debugging reducer the paper evaluates, the four real-world predicate (bug-reproducer) families used as subjects, and the scripts that regenerate the paper's tables. Every reducer treats its input as an opaque byte sequence and learns nothing about the format.

The headline result: **`drdd` matches the classical `ddmin` baseline's reduction quality while using a fraction of the oracle calls** — 1.7% on XML, 50% on FFmpeg — and, unlike ProbDD and CDD, without giving up 1-minimality.

> **Start here.** This page is the repository landing — orientation and a map. The **formal artifact document is [`README.txt`](README.txt)**, which follows the eight-section structure the ISSRE 2026 call requires and is self-contained (setup, a no-toolchain functionality check, and the full reproduction). For setup depth see [`REQUIREMENTS.md`](REQUIREMENTS.md) and [`INSTALL.md`](INSTALL.md).

## Reducers

Four reducers under [`src/reducers/`](src/reducers/), one per algorithm the paper evaluates.

| Reducer | Paper ref. | Strategy | Literature |
|---------|------------|----------|------------|
| [`ddmin`](src/reducers/ddmin.py)  | `ddmin`$^Y$ | Classical halving complement sweep with restart-after-success | Zeller & Hildebrandt |
| [`drdd`](src/reducers/drdd.py)    | **Dr. DD** | Halving complement sweep + deferred single-element causal-chain scan | — |
| [`probdd`](src/reducers/probdd.py)| ProbDD | Per-element removal probabilities, updated on each rejection | [Wang et al.](https://doi.org/10.1145/3468264.3468625) |
| [`cdd`](src/reducers/cdd.py)      | CDD | Deterministic counter-driven partition schedule (no restarts) | [Zhang et al.](https://doi.org/10.1109/ICSE55347.2025.00117) |

> **Naming.** The paper writes the simplified classical baseline as `ddmin`$^Y$ (the *Why Programs Fail* / Fuzzingbook form); in this code it is the reducer named `ddmin`. The paper's contribution, `drdd`, is "Dr. DD".

## Predicates

Four families of subjects, each a self-contained plugin under [`predicates/`](predicates/). Inputs ship in-tree; the oracle binaries are built from pinned upstream source by each family's `Makefile` (or baked into the container). Per-family build and provenance detail is in [`predicates/README.md`](predicates/README.md).

| Family | Cases | Bug type |
|--------|-------|----------|
| [XML](predicates/xml/) | 5 cases × 3 size variants | XQuery output discrepancy between two BaseX versions |
| [FFmpeg](predicates/ffmpeg/) | 14 cases | AddressSanitizer report under a specific filter |
| [Binutils](predicates/binutils/) | 12 cases | SIGSEGV / glibc heap corruption in `readelf`, `objdump`, `objcopy`, `nm` |
| [CrashJS](predicates/crashjs/) | 11 cases | `TypeError` reproduction in an instrumented `lodash` build |

## Repository layout

| Path | What it is | Documented in |
|------|------------|---------------|
| [`src/`](src/) | The installable, family-agnostic library: reducers, the oracle/family contracts, the plugin loader, the runner, and the benchmark harness. | — |
| [`predicates/`](predicates/) | The four subject families. Each is a `manifest.json` contract plus an `oracle.py`, its input `cases/`, and a `Makefile` where a build is needed. | [`predicates/README.md`](predicates/README.md) |
| [`cli/`](cli/) | `minimize` (one case, one reducer) and `bench` (a spec-selected matrix). Both family-agnostic. | [`cli/README.md`](cli/README.md) |
| [`benchmark/`](benchmark/) | The three experiment scripts that regenerate the paper's tables, the reproduction specs, and the `runs/` output. | [`benchmark/README.md`](benchmark/README.md) |
| [`Dockerfile`](Dockerfile) | A reproduction image that bakes in all four oracles. | [`README.txt`](README.txt) §7 |
| [`Makefile`](Makefile) | `make dist` (package the tracked file set), `make clean`. `make help` lists them. | — |

## Quick start

No toolchain, about 70 seconds — the XML family needs only a JRE, since its BaseX jars ship in-tree:

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -e .
cli/bench benchmark/specs/getting-started.json
```

The `result.csv` it writes reproduces row T-1e9bc83-1-1 of the paper's Table II exactly — `ddmin` 396 B / 32,567 calls and `drdd` 401 B / 1,618 calls. Full setup and the tiered reproduction (≈70 s / ≈2.2 h / ≈10 h) are in [`README.txt`](README.txt) §7–§8.

## Reproducing the paper

[`README.txt`](README.txt) §8 is the authoritative guide. In brief: build the oracle libs you need (`make -C predicates/<family>`), then

```bash
cli/bench benchmark/specs/reduced.json      # all 4 families × 4 reducers, ~2.2 h
python benchmark/scripts/drdd_issre.py      # the complete ~10 h main table
```

The three scripts in [`benchmark/scripts/`](benchmark/scripts/) map to the paper's tables — the main table (`drdd_issre.py`), the restart-budget study (`ablate_drdd.py`, Table V), and the lost-minimality study (`verify_competitors.py`, Table IV); see [`benchmark/README.md`](benchmark/README.md). The deterministic reducers reproduce their `(size, oracle-call)` pairs exactly; the two narrow exceptions (ProbDD's seed sensitivity and the ASLR-sensitive binutils `21409-2`) are documented in [`README.txt`](README.txt) §8.

## Extending it

The loader discovers any directory under `predicates/` holding a `manifest.json` and does what the manifest says, so **a new case or an entire new family plugs in with no change under `src/`**. The contract is specified in [`predicates/README.md`](predicates/README.md).

## Artifact evaluation

Targets the **Reproducible** badge (ISSRE's hierarchy: Reproducible ⊃ Reviewed ⊃ Available). Archived at [`10.5281/zenodo.21498483`](https://doi.org/10.5281/zenodo.21498483) under the MIT [`LICENSE`](LICENSE). The badge case is made in [`README.txt`](README.txt) §2.

## Provenance & license

Predicate subjects derive from public datasets and bug trackers — XML from Zhang et al.'s artifact, FFmpeg from trac tickets at pinned commits, binutils from sourceware Bugzilla, CrashJS from Zenodo record 10530515 — cited per family in [`predicates/README.md`](predicates/README.md) and distinct from this artifact's authorship. Released under the MIT License; see [`LICENSE`](LICENSE).

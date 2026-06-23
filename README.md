# Replication Package — *Dr. DD: 1-Minimal Isolation of Failure Causes via Deferred Restarts*

This is the replication package for the paper **"Dr. DD: 1-Minimal Isolation
of Failure Causes via Deferred Restarts"** (ISSRE 2026, under review). It
contains the implementations of every Delta Debugging algorithm evaluated in the
paper, the four real-world predicate (bug-reproducer) families used as subjects,
and the scripts that regenerate the paper's tables.

The artifact is **structure-agnostic**: every reducer treats its input as an
opaque byte sequence and learns nothing about the format. The headline claim is
that **Dr. DD (`drdd`) preserves 1-minimality while using substantially fewer
oracle calls than the classical `ddmin` baseline**, and that the no-restart
competitors (`probdd`, `cdd`) buy their efficiency only by giving up
1-minimality.

This README is the entry point. It consolidates the system requirements, gives a
fast "kick-the-tires" path, then a full step-by-step reproduction, and maps each
paper table to the exact command that regenerates it. Family-specific build and
provenance details live in the sub-READMEs linked throughout.

## Targeted ACM badges

This package is structured against the
[ACM Artifact Review and Badging policy (current)](https://www.acm.org/publications/policies/artifact-review-and-badging-current):

| Badge | How this package supports it |
|-------|------------------------------|
| **Artifacts Available** | The complete package is archived with a DOI (see *Data Availability* in the paper) and self-contained: all source, predicate inputs, and build recipes are included. |
| **Artifacts Evaluated — Functional / Reusable** | Every component documented here is runnable as described. The reducers are a small, family-agnostic library; new predicate families and cases plug in without touching `src/` (see *Reusability*). |
| **Results Reproduced** | [`benchmark/scripts/drdd_issre.py`](benchmark/scripts/drdd_issre.py) regenerates the per-case minimized length and oracle-call counts of the paper's main table; the two supplementary scripts regenerate the ablation and verification tables. See *Reproducing the paper's tables* and *Reproduction caveats*. |

## Overview

Five reducers are implemented under [`src/reducers/`](src/reducers/); four are
reported in the paper.

| Reducer | Paper name | Strategy | 1-minimal? | Determinism | Literature |
|---------|-----------|----------|:----------:|:-----------:|------------|
| [`ddmin`](src/reducers/ddmin.py)  | `ddmin`$^Y$ | Classical halving complement sweep with restart-after-success | yes | deterministic | Zeller & Hildebrandt |
| [`drdd`](src/reducers/drdd.py)    | **Dr. DD** *(this paper)* | Halving complement sweep + deferred single-element causal-chain scan | yes (at `R=∣I∣`) | deterministic | — |
| [`probdd`](src/reducers/probdd.py)| ProbDD | Per-element removal probabilities, updated on each rejection | no | **stochastic** | [Wang et al.](https://doi.org/10.1145/3468264.3468625) |
| [`cdd`](src/reducers/cdd.py)      | CDD | Deterministic counter-driven partition schedule (no restarts) | no | deterministic | [Zhang et al.](https://doi.org/10.1109/ICSE55347.2025.00117) |
| [`pmadd`](src/reducers/pmadd.py)  | *(not reported)* | Monotonicity-aware skipping via confidence scoring | — | — | [Tao et al.](https://doi.org/10.1145/3756681.3756940) |

> **Note on naming.** The paper writes the simplified classical baseline as
> `ddmin`$^Y$ (the *Why Programs Fail* / Fuzzingbook form). In this code it is the
> reducer named `ddmin`. The paper's contribution, `drdd`, is "Dr. DD".
> `pmadd` is an auxiliary reducer included for completeness; it is **not** part of
> any reported table and is excluded by the main reproduction script.

The reducers are evaluated against four predicate families, each a self-contained
plugin under [`predicates/`](predicates/):

| Family | Cases | Bug type |
|--------|-------|----------|
| [XML](predicates/xml/) | 5 cases × 3 size variants | XQuery output discrepancy between two BaseX versions |
| [FFmpeg](predicates/ffmpeg/) | 16 cases (14 reported) | AddressSanitizer report under a specific filter |
| [Binutils](predicates/binutils/) | 12 cases | SIGSEGV / glibc heap corruption in `readelf`, `objdump`, `objcopy`, `nm` |
| [CrashJS](predicates/crashjs/) | 11 cases | `TypeError` reproduction in an instrumented `lodash` build |

All predicate **inputs** are shipped in-tree. The **oracle binaries/libraries**
are *not* shipped — they are built from upstream source by each family's
`Makefile` (see *Step-by-step reproduction*). This is the single biggest source
of reproduction friction, so the per-family build steps are documented carefully
in [`predicates/README.md`](predicates/README.md).

## Repository layout

| Path | Description |
|------|-------------|
| [`src/`](src/) | The installable, family-agnostic library: reducers, the oracle/family contracts, the predicate plugin loader, the minimization runner, loggers, and the benchmark harness. **Reproduction does not require editing anything here.** |
| [`cli/`](cli/) | Command-line entry points: `minimize` (one case, any reducer), `bench` (spec-selected subset run), `cherrypick_xml` (XML seed-variant generator). See [`cli/README.md`](cli/README.md). |
| [`benchmark/`](benchmark/) | The three experiment scripts that regenerate the paper's tables, and the `runs/` output directory. See [`benchmark/README.md`](benchmark/README.md). |
| [`predicates/`](predicates/) | The four predicate families. Each ships an `oracle.py`, a `manifest.json` (cases + config), a `cases/` directory of inputs, and a `Makefile` that builds the oracle lib. See [`predicates/README.md`](predicates/README.md). |

## System requirements

The paper's experiments ran on Fedora Linux (x86_64) on an AMD Ryzen
workstation with 64 GB RAM, pinned to 2 quarantined (isolated, fixed-frequency)
cores so timing is reproducible and undisturbed by other load. On that setup a
full benchmark run takes **~11 hours**; use this as a baseline for the expected
duration. Any modern x86_64 Linux host should reproduce the results; the build
steps assume a Linux toolchain.

**Core (always required):**

- Linux, x86_64
- Python ≥ 3.11
- Network access (the family `Makefile`s clone/download upstream sources)
- Several GB of free disk (the binutils and FFmpeg builds clone large upstream repos)

**Per-family build prerequisites** (only needed for the families you intend to run):

| Family | Build command | Toolchain needed |
|--------|---------------|------------------|
| XML | `make -C predicates/xml` | Java 11+ (for the bundled BaseX jars; Saxon ships inside the `saxonche` wheel) |
| FFmpeg | `make -C predicates/ffmpeg` | `clang` (builds an ASan FFmpeg from source at two pinned commits) |
| Binutils | `make -C predicates/binutils` | `gcc` **plus `flex`, `bison`, `m4`** |
| CrashJS | `make -C predicates/crashjs` | `node` (any modern version; tested on Node 22) |

> **Binutils gotcha.** Without `flex`/`bison`/`m4` the build fails with
> `Error 127`. If a build is interrupted, a stale `config.cache` can cause a
> later `"YACC has changed since the previous run"` error — recover with
> `rm -rf predicates/binutils/build/build-*` and rebuild.

Python dependencies (`defusedxml`, `saxonche`, `numpy`) are declared in
[`pyproject.toml`](pyproject.toml) and installed by the setup step below. Nothing
is published to PyPI; the scripts run in place with `PYTHONPATH=src`.

## Reproducing in a container (recommended)

The most reliable way to reproduce the paper is the bundled
[`Dockerfile`](Dockerfile), which freezes the whole environment — OS, Python,
Java, `clang`, the binutils build tools, and Node — and **bakes in all four
oracle libraries at build time**. A reviewer then needs none of the host
toolchain above and no per-family build. The image is standard OCI and builds
with either [Podman](https://podman.io) (rootless, the default on Fedora) or
Docker; the commands are identical apart from the binary name.

```bash
# Build the image. Clones binutils-gdb + FFmpeg and compiles an ASan FFmpeg, so
# it needs network access and ~30-60 min the first time; the image is several GB.
podman build -t drdd .                    # or: docker build -t drdd .

# Regenerate the main table (one result.csv per family); mount a host dir so the
# output survives the container. The :Z suffix relabels the mount for SELinux
# (required on Fedora/RHEL; harmless on other hosts and ignored by Docker):
podman run --rm -v "$PWD/runs:/artifact/benchmark/runs:Z" drdd \
    python benchmark/scripts/drdd_issre.py

# Or open a shell and run anything from the sections below interactively:
podman run --rm -it drdd
#   (inside) python benchmark/scripts/ablate_drdd.py
#   (inside) cli/minimize crashjs 9 --reducer drdd --verbose
```

Every command in the rest of this README works unchanged inside the container
shell (`PYTHONPATH` is already set).

> **AddressSanitizer note.** The FFmpeg oracle is an ASan build. On some recent
> kernels ASan cannot map its shadow memory under high-entropy ASLR; if the
> FFmpeg family aborts at startup with an ASan mmap/shadow-memory message, lower
> the host setting once with `sudo sysctl -w vm.mmap_rnd_bits=28` and re-run (the
> container shares the host kernel, so this is set on the host, not in the image).

To set up host-natively instead of using the container, follow **Setup** below.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .          # installs the declared dependencies
```

All commands in this README are run **from the repository root** with
`PYTHONPATH=src` (the `cli/*` wrappers set this for you).

## Getting started (kick the tires, ~minutes)

Start with the cheapest family to confirm the toolchain works end to end. CrashJS
and binutils are the fastest — seconds to about a minute per `(case × reducer)`.

```bash
# 1. Build one fast oracle lib
make -C predicates/crashjs

# 2. Minimize a single case with the paper's method and the baseline
PYTHONPATH=src cli/minimize crashjs 9 --reducer drdd  --verbose
PYTHONPATH=src cli/minimize crashjs 9 --reducer ddmin --verbose
```

`drdd` should reach the same minimized length as `ddmin` while reporting far
fewer oracle calls — the paper's core claim, visible on a single case.

## Reproducing the paper's tables

The full reproduction is driven by three scripts in
[`benchmark/scripts/`](benchmark/scripts/). Each writes a timestamped directory
under `benchmark/runs/`. Build the oracle lib for each family you want to include
first (a family whose lib is missing is reported and skipped, so the rest still
run).

```bash
# Build all four oracle libs (skip any family you don't need)
make -C predicates/xml
make -C predicates/ffmpeg
make -C predicates/binutils
make -C predicates/crashjs

# Main reproduction: minimized length + oracle calls per (family × case × reducer)
PYTHONPATH=src python benchmark/scripts/drdd_issre.py

# Supplementary studies
PYTHONPATH=src python benchmark/scripts/ablate_drdd.py        # restart-budget R sweep
PYTHONPATH=src python benchmark/scripts/verify_competitors.py # ProbDD/CDD 1-minimality check
```

### Claim → command → table

| Paper claim / table | Command | What it produces |
|---------------------|---------|------------------|
| **Main table** — per-case minimized size, oracle calls, and (derived) wall-clock time / relative metrics for `ddmin`, `drdd`, `probdd`, `cdd` (paper Tables I–III) | `benchmark/scripts/drdd_issre.py` | One run dir per family with `result.csv` (per-task minimized length + oracle calls + wall time) and full per-run logs |
| **RQ on the restart budget** — effect of `R ∈ {1,2,4,8,∣I∣}` on oracle calls, output size, and 1-minimality (paper Table V) | `benchmark/scripts/ablate_drdd.py` | `results.csv` plus per-family and per-`R` aggregate CSVs |
| **RQ on lost minimality** — bytes a single-element fixed-point scan still removes from `probdd`/`cdd` outputs (paper Table IV) | `benchmark/scripts/verify_competitors.py` | `results.csv` quantifying how far each competitor stops short of 1-minimality |

**How to check a reproduction.** Compare the per-case `minimized_length` and
oracle-call columns in the generated `result.csv` against the corresponding rows
of the paper's tables (e.g. Table II / `tab:oracles` for the main table). The
deterministic reducers (`ddmin`, `drdd`, `cdd`) should match the reported
`(length, oracle-call)` pairs; see the caveats below for the two documented
exceptions.

## Reproduction caveats

The results reproduce deterministically, with two narrow and well-understood
exceptions — neither affects any conclusion in the paper:

- **`probdd` is stochastic by design.** ProbDD is a probabilistic algorithm, so
  its oracle-call counts shift from run to run and need not match the reported
  figures exactly; treat its rows as indicative. The reducers that carry the
  paper's claims — `drdd`, the `ddmin` baseline, and `cdd` — are deterministic
  and match exactly.
- **One binutils case (`21409-2`) has ASLR-dependent call counts.** With ASLR on
  (as in the original runs), a borderline `objdump` access faults in some memory
  layouts but not others, nudging this single case's call count by a few; its
  minimized **length is identical** every run.

A few practical notes, not deviations: `pmadd` is an auxiliary reducer in no
paper table (the main script skips it); FFmpeg ships all 16 collected cases, of
which the paper reports 14; and runtimes range from seconds per task (binutils,
CrashJS) to minutes (FFmpeg, XML — where most candidate inputs are malformed and
correctly rejected, so a high reject rate is expected). A full run is ~11 hours
on the benchmark setup above, so spot-check a family via `cli/bench` first.

## Reusability — adding a predicate family or case

The library auto-discovers any directory under `predicates/` that contains both
an `oracle.py` (one `Oracle` subclass) and a `manifest.json` (cases + config), so
**new families and cases plug in without any change under `src/`**:

- **A new case** in an existing family: add its input under `cases/<id>/` and an
  entry in that family's `manifest.json`. It is then selectable as
  `cli/minimize <family> <id>` and included in benchmark runs.
- **A new family**: create `predicates/<name>/` with an `oracle.py`,
  `manifest.json`, `cases/`, and (if it needs a built oracle) a `Makefile`.

See [`predicates/README.md`](predicates/README.md) for the family/manifest
contract and [`cli/README.md`](cli/README.md) for how cases are selected.

## Documentation map

| Document | Contents |
|----------|----------|
| This file | Overview, requirements, getting started, table reproduction, caveats |
| [`predicates/README.md`](predicates/README.md) | Per-family layout, build steps, reproduce commands, and data provenance |
| [`benchmark/README.md`](benchmark/README.md) | The three experiment scripts and their output format |
| [`cli/README.md`](cli/README.md) | `minimize`, `bench`, `cherrypick_xml` usage and spec format |

## Data provenance

The predicate subjects are derived from public datasets and bug trackers, cited
in [`predicates/README.md`](predicates/README.md): XML from the replication
artifact of Zhang et al.; FFmpeg from FFmpeg trac tickets at pinned upstream
commits; binutils from sourceware bugzilla; CrashJS from the public CrashJS
dataset (Zenodo record 10530515). These are citations of others' work and are
distinct from the (anonymized) authorship of this artifact.

## License

Released under the MIT License — see [`LICENSE`](LICENSE).

# Replication Package — ISSRE '26 Paper 238

This is the replication package for the paper **"Dr. DD: 1-Minimal Isolation of Failure Causes via Deferred Restarts"** (ISSRE 2026, under review). It contains the implementations of every Delta Debugging algorithm evaluated in the paper, the four real-world predicate (bug-reproducer) families used as subjects, and the scripts that regenerate the paper's tables.

The artifact is structure-agnostic: every reducer treats its input as an opaque byte sequence and learns nothing about the format.

This README is the entry point. It walks from a container or host-native setup through a quick smoke test to the full reproduction, mapping each paper table to the command that regenerates it. Family-specific build and provenance details live in the sub-READMEs linked throughout.

## Overview

### Reducers

Four reducers are implemented under [`src/reducers/`](src/reducers/), one per algorithm the paper evaluates.

| Reducer | Paper ref. | Strategy | Literature |
|---------|------------|----------|------|
| [`ddmin`](src/reducers/ddmin.py)  | `ddmin`$^Y$ | Classical halving complement sweep with restart-after-success | Zeller & Hildebrandt |
| [`drdd`](src/reducers/drdd.py)    | **Dr. DD** | Halving complement sweep + deferred single-element causal-chain scan | — |
| [`probdd`](src/reducers/probdd.py)| ProbDD | Per-element removal probabilities, updated on each rejection | [Wang et al.](https://doi.org/10.1145/3468264.3468625) |
| [`cdd`](src/reducers/cdd.py)      | CDD | Deterministic counter-driven partition schedule (no restarts) | [Zhang et al.](https://doi.org/10.1109/ICSE55347.2025.00117) |

> **Note on naming.** The paper writes the simplified classical baseline as `ddmin`$^Y$ (the *Why Programs Fail* / Fuzzingbook form). In this code it is the reducer named `ddmin`. The paper's contribution, `drdd`, is "Dr. DD".

### Predicates

The reducers are evaluated against four predicate families, each a self-contained plugin under [`predicates/`](predicates/).

| Family | Cases | Bug type |
|--------|-------|----------|
| [XML](predicates/xml/) | 5 cases × 3 size variants | XQuery output discrepancy between two BaseX versions |
| [FFmpeg](predicates/ffmpeg/) | 14 cases | AddressSanitizer report under a specific filter |
| [Binutils](predicates/binutils/) | 12 cases | SIGSEGV / glibc heap corruption in `readelf`, `objdump`, `objcopy`, `nm` |
| [CrashJS](predicates/crashjs/) | 11 cases | `TypeError` reproduction in an instrumented `lodash` build |

All predicate inputs are shipped in-tree. The oracle binaries/libraries are *not* shipped — they are built from upstream source by each family's `Makefile`; the per-family build steps are documented in [`predicates/README.md`](predicates/README.md).

## Repository layout

| Path | Description |
|------|-------------|
| [`src/`](src/) | The installable, family-agnostic library: reducers, the oracle/family contracts, the predicate plugin loader, the minimization runner, loggers, and the benchmark harness. |
| [`cli/`](cli/) | Command-line entry points: `minimize` (one case, any reducer), `bench` (spec-selected subset run), `cherrypick_xml` (XML seed-variant generator). See [`cli/README.md`](cli/README.md). |
| [`benchmark/`](benchmark/) | The three experiment scripts that regenerate the paper's tables, and the `runs/` output directory. See [`benchmark/README.md`](benchmark/README.md). |
| [`predicates/`](predicates/) | The four predicate families. Each ships an `oracle.py`, a `manifest.json` (cases + config), a `cases/` directory of inputs, and a `Makefile` that builds the oracle lib. See [`predicates/README.md`](predicates/README.md). |

## Reproducing in a container (recommended)

The bundled [`Dockerfile`](Dockerfile) freezes the whole environment — OS, Python, Java, `clang`, the binutils build tools, and Node — and **bakes in all four oracle libraries at build time**. A reviewer then needs none of the host toolchain or per-family builds described under *Running locally* below. The image is standard OCI and builds with either [Podman](https://podman.io) (rootless, the default on Fedora) or Docker; the commands are identical apart from the binary name.

```bash
# Build the image. Clones binutils-gdb + FFmpeg 
# and compiles an ASan FFmpeg, so needs network 
# access and ~30-60 min the first time; the image 
# is several GB.
podman build -t drdd .

# Regenerate the main table (one result.csv per 
# family); mount a host dir so the output survives 
# the container. The :Z suffix relabels the mount 
# for SELinux (required on Fedora/RHEL; harmless 
# on other hosts and ignored by Docker). The seccomp 
# flag is required for the binutils family (see note 
# below).
podman run --rm --security-opt seccomp=unconfined -v "$PWD/runs:/artifact/benchmark/runs:Z" drdd python benchmark/scripts/drdd_issre.py

# Or open a shell and run anything from the sections 
# below interactively (no setup required):
podman run --rm --security-opt seccomp=unconfined -it drdd
```

> **Binutils / seccomp note.** The binutils oracle runs each target under `setarch -R` to disable ASLR, so the one layout-sensitive case (`21409-2`) is deterministic. That relies on the `personality(ADDR_NO_RANDOMIZE)` syscall, which the default container seccomp profile blocks — hence `--security-opt seccomp=unconfined` on the `run` commands above. Without it, `setarch` aborts before the tool executes and the binutils family cannot reproduce. (On a host, no flag is needed.)

> **AddressSanitizer note.** The FFmpeg oracle is an ASan build. On some recent kernels ASan cannot map its shadow memory under high-entropy ASLR; if the FFmpeg family aborts at startup with an ASan mmap/shadow-memory message, lower the host setting once with `sudo sysctl -w vm.mmap_rnd_bits=28` and re-run (the container shares the host kernel, so this is set on the host, not in the image).

Every command in the rest of this README works unchanged inside the container shell (the package is already `pip install -e .`'d into the image). To run directly on a host instead of the container, see *Running locally* below.

## Running locally

Host-native setup needs:

- Linux, x86_64
- Python ≥ 3.11
- Network access (the family `Makefile`s clone/download upstream sources)
- Several GB of free disk (the binutils and FFmpeg builds clone large upstream repos)

Set up the Python environment from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e . # installs the dependencies and the library itself
```
> **Executable permissions.** The `cli/*` scripts ship with the executable bit set, but some archive tools (and `unzip`) drop it on extraction. If you get a `Permission denied`, restore it once with `chmod +x cli/*`.


The editable install puts the library packages (`reducers`, `loader`, `bench`, ...) on the import path — as long as the venv is active, every command below works as written. Keep the venv active (`source .venv/bin/activate`) in each shell, and run the commands from the repository root — they're written with repo-root-relative paths like `cli/minimize` and `make -C predicates/...`. The dependencies (`defusedxml`, `saxonche`, `numpy`) are declared in [`pyproject.toml`](pyproject.toml).

### Building the oracle libraries

Each family builds its oracle from upstream source; build only the ones you intend to run:

| Family | Build command | Toolchain needed |
|--------|---------------|------------------|
| XML | N/A | Java 11+ at run time (for the bundled BaseX servers; Saxon ships inside the `saxonche` wheel) |
| FFmpeg | `make -C predicates/ffmpeg` | `clang` (builds an ASan FFmpeg from source at two pinned commits) |
| Binutils | `make -C predicates/binutils` | `gcc` plus `flex`, `bison`, `m4` |
| CrashJS | `make -C predicates/crashjs` | `node` (any modern version; tested on Node 22) |

> **Binutils gotcha.** Without `flex`/`bison`/`m4` the build fails with `Error 127`. If a build is interrupted, a stale `config.cache` can cause a later `"YACC has changed since the previous run"` error — recover with `rm -rf predicates/binutils/build/build-*` and rebuild.

## Smoke check 

Start with the cheapest family to confirm the toolchain works end to end. CrashJS and binutils are the fastest — seconds to about a minute per `(case × reducer)`.

```bash
# 1. Build one fast oracle lib
make -C predicates/crashjs

# 2. Minimize a single case with the paper's method
cli/minimize crashjs 9 --reducer drdd  --verbose
cli/minimize crashjs 9 --reducer ddmin --verbose
```

`drdd` should reach the same minimized length as `ddmin` while reporting far fewer oracle calls — the paper's core claim, visible on a single case.

## Reproducing the paper's results

The full reproduction is driven by three scripts in [`benchmark/scripts/`](benchmark/scripts/). Each writes a timestamped directory under `benchmark/runs/`. Build the oracle lib for each family you want to include first; a family whose lib is missing is reported and skipped, so the rest still run.

```bash
# Build the three oracle libs that aren't prebuilt 
# (skip any family you don't need); XML needs no 
# build step.
make -C predicates/ffmpeg
make -C predicates/binutils
make -C predicates/crashjs

# Main reproduction: minimized length + oracle 
# calls per (family × case × reducer)
python benchmark/scripts/drdd_issre.py

# Supplementary studies
python benchmark/scripts/ablate_drdd.py
python benchmark/scripts/verify_competitors.py
```

### What each script reproduces

The scripts (run as shown in the block above) map to the paper as follows:

| Script | Reproduces | Output |
|--------|------------|--------|
| [`drdd_issre.py`](benchmark/scripts/drdd_issre.py) | **Main table** — per-case minimized size, oracle calls, and (derived) wall-clock time / relative metrics for `ddmin`, `drdd`, `probdd`, `cdd` (paper Tables I–III) | One run dir per family with `result.csv` (per-task minimized length + oracle calls + wall time) and full per-run logs |
| [`ablate_drdd.py`](benchmark/scripts/ablate_drdd.py) | **Restart-budget RQ** — effect of `R ∈ {1,2,4,8,∣I∣}` on oracle calls, output size, and 1-minimality (paper Table V) | `results.csv` plus per-family and per-`R` aggregate CSVs |
| [`verify_competitors.py`](benchmark/scripts/verify_competitors.py) | **Lost-minimality RQ** — bytes a single-element fixed-point scan still removes from `probdd`/`cdd` outputs (paper Table IV) | `results.csv` quantifying how far each competitor stops short of 1-minimality |

**Checking a match.** The deterministic reducers (`ddmin`, `drdd`, `cdd`) should reproduce the paper's `(minimized_length, oracle-calls)` pairs **exactly** — compare `result.csv` against Table II (`tab:oracles`). The two documented exceptions are below.

## Reproduction caveats

The results reproduce deterministically, with two narrow and well-understood exceptions — neither affects any conclusion in the paper:

- **`probdd` is stochastic by design, but pinned for replication.** ProbDD is a probabilistic algorithm; we fix its RNG seed to `0` (the default in [`src/reducers/probdd.py`](src/reducers/probdd.py)), so every run is reproducible and re-running yields identical oracle-call counts rather than shifting figures. Its numbers should match the reported ones on the same platform; they are only guaranteed stable *across* hosts insofar as the NumPy RNG and floating-point results agree. Removing the seed restores the run-to-run variation inherent to the algorithm.

- **One binutils case (`21409-2`) is address-space-layout sensitive.** A borderline `objdump` access faults under some memory layouts but not others, so under ASLR this case is not exactly reproducible. The binutils oracle runs the target under `setarch -R` (ASLR disabled) to pin the layout, making the case deterministic and reproducible run-to-run; its figures therefore differ by a small amount (a few oracle calls, and a few bytes of output for the non-1-minimal competitors) from the ASLR-on sample originally reported.

**Runtime.** Per-task time ranges from seconds (binutils, CrashJS) to minutes (FFmpeg, XML — where most candidate inputs are malformed and correctly rejected, so a high reject rate is expected). The paper's full run took **~11 hours** on the reference setup (Fedora Linux x86_64, AMD Ryzen, 64 GB RAM, 2 pinned cores); spot-check a family via `cli/bench` first.

## Reusability

The library auto-discovers any directory under `predicates/` that contains both an `oracle.py` (one `Oracle` subclass) and a `manifest.json` (cases + config), so **new families and cases plug in without any change under `src/`**:

- **A new case** in an existing family: add its input under `cases/<id>/` and an entry in that family's `manifest.json`. It is then selectable as `cli/minimize <family> <id>` and included in benchmark runs.

- **A new family**: create `predicates/<name>/` with an `oracle.py`, `manifest.json`, `cases/`, and (if it needs a built oracle) a `Makefile`.

See [`predicates/README.md`](predicates/README.md) for the family/manifest contract and [`cli/README.md`](cli/README.md) for how cases are selected.

## ACM badges

This package is structured against the [ACM Artifact Review and Badging policy (current)](https://www.acm.org/publications/policies/artifact-review-and-badging-current):

| Badge | How this package supports it |
|-------|------------------------------|
| **Artifacts Available** | The complete package is archived with a DOI (see *Data Availability* in the paper) and self-contained: all source, predicate inputs, and build recipes are included. |
| **Artifacts Evaluated — Functional / Reusable** | Every component documented here is runnable as described. The reducers are a small, family-agnostic library; new predicate families and cases plug in without touching `src/` (see *Reusability*). |
| **Results Reproduced** | [`benchmark/scripts/drdd_issre.py`](benchmark/scripts/drdd_issre.py) regenerates the per-case minimized length and oracle-call counts of the paper's main table; the two supplementary scripts regenerate the ablation and verification tables. See *Reproducing the paper's results* and *Reproduction caveats*. |

## Data provenance

The predicate subjects are derived from public datasets and bug trackers, cited in [`predicates/README.md`](predicates/README.md): XML from the replication artifact of Zhang et al.; FFmpeg from FFmpeg trac tickets at pinned upstream commits; binutils from sourceware bugzilla; CrashJS from the public CrashJS dataset (Zenodo record 10530515). These are citations of others' work and are distinct from the (anonymized) authorship of this artifact.

## License

Released under the MIT License — see [`LICENSE`](LICENSE).

# Benchmark Suite

Reproduces the paper's results (Dr. DD, ISSRE 2026). The experiments live in `benchmark/scripts/`; each writes a timestamped run directory under `benchmark/runs/`. Run them from the repo root with the venv active (after `pip install -e .` — no `PYTHONPATH` needed).

For ad-hoc, spec-selected runs (a subset of reducers/families/cases) use the general `cli/bench` tool instead — see [cli/README.md](../cli/README.md).

## Reproduction at three scales

Two ready-made `cli/bench` specs sit in [`specs/`](specs/), for reviewers who don't want the full ~10 h run. Both are plain JSON and editable.

| Command | Covers | Cost |
|---------|--------|------|
| `cli/bench benchmark/specs/getting-started.json` | XML case `1.1`, `ddmin` + `drdd` — reproduces one Table II row | ~70 s, **no oracle build** (XML jars ship in-tree) |
| `cli/bench benchmark/specs/reduced.json` | all four families × four reducers, minus the three costliest FFmpeg cases and the larger XML variants | ~2.2 h + builds |
| `python benchmark/scripts/drdd_issre.py` | all 52 subjects × four reducers — the complete main table | ~10 h + builds |

`reduced.json` records what it omits and why, inline. The full guide is [`../README.txt`](../README.txt) §8.

## Prerequisites

Each family's oracle needs its lib built first (the scripts skip or abort on a missing one). XML is the exception — its BaseX jars and inputs ship in-tree, so it needs no build, only a JRE at run time:

| Family   | Build                          | Also needs    |
|----------|--------------------------------|---------------|
| xml      | *none (ships prebuilt)*        | Java 11+ (run)|
| ffmpeg   | `make -C predicates/ffmpeg`    | clang         |
| binutils | `make -C predicates/binutils`  | flex/bison/m4 |
| crashjs  | `make -C predicates/crashjs`   | node          |

Case ids come from each family's `manifest.json` (binutils/ffmpeg ids are bug/ticket numbers, crashjs `1`..`11`, xml `1.1`..`5.3`).

## Scripts

### `drdd_issre.py` — main reproduction (Table II)

Runs the four reported reducers (`ddmin`, `probdd`, `cdd`, `drdd`) against every case of all four families, writing one run dir per family — the main table. To check a reproduction, compare the per-case `minimized_length` and oracle-call columns of the generated `result.csv` against the corresponding rows of the paper's tables (Table II / `tab:oracles` for size and oracle calls). The deterministic reducers (`ddmin`, `cdd`, `drdd`) should match the reported `(length, oracle-call)` pairs exactly.

Two documented exceptions, both detailed in [`../README.txt`](../README.txt) section 8: ProbDD's RNG seed is fixed at `0`, so it re-runs identically on a given host but is only stable *across* hosts insofar as the NumPy RNG and floating-point results agree; and one binutils case (`21409-2`) is ASLR-sensitive, so its oracle-call count moves by a few between runs, and with it a few bytes of output for the non-1-minimal competitors.

```bash
python benchmark/scripts/drdd_issre.py
```

### `ablate_drdd.py` — drdd R-ablation study

Sweeps drdd's restart budget `R` (its `c_iters`) over a subject set and records the cost / quality / 1-minimality tradeoff at each budget, plus per-family and per-R aggregates. `R = |I|` resolves causal chains to a 1-minimal output; `R = 1` is a single linear pass. Edit `R_VALUES` / `SUBJECTS` to expand the study.

```bash
python benchmark/scripts/ablate_drdd.py
```

### `verify_competitors.py` — ProbDD/CDD non-1-minimality

Regenerates each competitor's reduced output and drives the single-element fixed-point scan ([`causal_chain_scan`](../src/reducers/drdd.py), the same verifier the ablation uses) over it: any byte it removes is one the competitor left behind, quantifying how far ProbDD and CDD stop short of 1-minimality. Edit `ALGORITHMS` / `SUBJECTS` to expand the study.

```bash
python benchmark/scripts/verify_competitors.py
```

## Output

Each run creates a directory under `benchmark/runs/`, named `<label>_<DD-MM-YYYY>_<HH:MM>_git-<sha>/`. The main reproduction writes:

| File                                 | Contents                |
|--------------------------------------|-------------------------|
| `result.csv`                         | Per-task metrics        |
| `logs/<n>_<predicate>_<reducer>.log` | Full minimization trace |

The two studies write a `results.csv` plus per-family and per-R / per-algorithm aggregate CSVs in their run dir.

`result.csv` records `input_sha256` per task alongside the metrics, so a run always carries proof of which input produced it — the one check that catches a subject having drifted from the one a reported figure was measured on.

Shared helpers for the experiment scripts live in [`scripts/_common.py`](scripts/_common.py): case lookup, the run-output root, and `verify_minimal`, the single definition of the 1-minimality check both studies use.

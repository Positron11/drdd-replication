# Benchmark Suite

Reproduces the paper's results (Dr. DD, ISSRE 2026). The experiments live in `benchmark/scripts/`; each writes a timestamped run directory under `benchmark/runs/`. Run them from the repo root with the venv active (after `pip install -e .` — no `PYTHONPATH` needed).

For ad-hoc, spec-selected runs (a subset of reducers/families/cases) use the general `cli/bench` tool instead — see [cli/README.md](../cli/README.md).

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

Runs the four reported reducers (`ddmin`, `probdd`, `cdd`, `drdd`) against every case of all four families, writing one run dir per family — the main table. To check a reproduction, compare the per-case `minimized_length` and oracle-call columns of the generated `result.csv` against the corresponding rows of the paper's tables (Table II / `tab:oracles` for size and oracle calls). The deterministic reducers (`ddmin`, `cdd`, `drdd`) should match the reported `(length, oracle-call)` pairs exactly; ProbDD is stochastic, so its counts vary slightly between runs. One binutils case (`21409-2`) is ASLR-sensitive: its minimized length matches but its oracle-call count varies by a few. See the *Reproduction caveats* in the [root README](../README.md).

```bash
python benchmark/scripts/drdd_issre.py
```

### `ablate_drdd.py` — drdd R-ablation study

Sweeps drdd's restart budget `R` (its `c_iters`) over a subject set and records the cost / quality / 1-minimality tradeoff at each budget, plus per-family and per-R aggregates. `R = |I|` resolves causal chains to a 1-minimal output; `R = 1` is a single linear pass. Edit `R_VALUES` / `SUBJECTS` to expand the study.

```bash
python benchmark/scripts/ablate_drdd.py
```

### `verify_competitors.py` — ProbDD/CDD non-1-minimality

Regenerates each competitor's reduced output and drives drdd's single-element fixed-point scan over it: any byte it removes is one the competitor left behind, quantifying how far ProbDD and CDD stop short of 1-minimality. Edit `ALGORITHMS` / `SUBJECTS` to expand the study.

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

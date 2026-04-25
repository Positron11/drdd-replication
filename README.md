# Delta Debugging Benchmark Suite

> Implementations and benchmarks of five Delta Debugging algorithms against real-world bug-reproducing predicates.

This repository implements five Delta Debugging algorithms and benchmarks them against two distinct families of real-world predicates: XML query discrepancy bugs (structured inputs) and FFmpeg memory-safety crashes (unstructured inputs).

## Algorithms

| Algorithm | Strategy | Literature |
|-----------|----------|------------|
| [`DDMin`](src/algos/ddmin.py) | Classical binary search over subsets | -
| [`DDPrime`](src/algos/ddprime.py) | Halving complement sweep + causal chain scan | -
| [`ProbDD`](src/algos/probdd.py) | Per-element removal probabilities, updated on failure | [Wang et al.](https://doi.org/10.1145/3468264.3468625)
| [`CDD`](src/algos/cdd.py) | Adaptive subset sizing with probabilistic decay | [Zhang et al.](https://doi.org/10.1109/ICSE55347.2025.00117)
| [`PmaDD`](src/algos/pmadd.py) | Monotonicity-aware skipping via confidence scoring | [Tao et al.](https://doi.org/10.1145/3756681.3756940)

> [!NOTE] 
> DDPrime is an original contribution by researchers associated with this project.

## Predicates

| Family | Cases | Bug type |
|--------|-------|----------|
| [XML](predicates/xml/) | 5 cases $\times$ 3 variants | XQuery output discrepancy between BaseX versions |
| [FFmpeg](predicates/ffmpeg/) | 14 cases | ASAN heap-buffer-overflow / LeakSanitizer |
| [Binutils](predicates/binutils/) | 12 cases | SIGSEGV / glibc heap corruption in `readelf`, `objdump`, `objcopy`, `nm` |
| [CrashJS](predicates/crashjs/) | 11 cases | TypeError reproduction in instrumented `lodash` via Syntest-generated mocha tests |

## Setup

### Requirements

- Python 3.11
- Java 11+

Set up the repository for use by installing the included modules:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Getting Started

- **Minimize an input** — see [scripts/README.md](scripts/README.md)
- **Run the benchmark suite** — see [benchmark/README.md](benchmark/README.md)
- **Explore predicate cases** — see [predicates/README.md](predicates/README.md)

## Repository Layout

| Path | Description |
|------|-------------|
| `src/` | Algorithms, benchmark harness, oracle core, and drivers |
| `scripts/` | `minimize_xml`, `minimize_ffmpeg`, `cherrypick_xml` |
| `predicates/` | XML and FFmpeg bug-reproducing predicate cases |
| `benchmark/` | Benchmark scripts and result runs |
| `tests/` | Sanity tests |
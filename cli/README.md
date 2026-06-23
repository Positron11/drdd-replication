# CLI

Command-line tools for minimization, benchmarking, and input preparation. Run from the repo root with the venv active — after `pip install -e .` the library is on the import path, so no `PYTHONPATH` is needed. If extraction dropped the executable bit, run `chmod +x cli/*` once or invoke via `python cli/<tool>`.

## `minimize`

Minimizes one predicate input with a DD-family reducer. The case is selected from its family's `manifest.json` by id — the input path and oracle config come from the manifest, so the script never hard-codes predicate paths.

```
usage: minimize <family> <case> [--reducer NAME] [--output PATH] [--verbose]

  family      one of: binutils, crashjs, ffmpeg, xml
  case        case id (see the family's manifest.json)
  --reducer   one of: cdd, ddmin, drdd, probdd  (default: ddmin)
  --output    output path  (default: input name with a .min suffix)
  --verbose   print per-step progress
```

```bash
cli/minimize binutils 21135 --reducer ddmin --verbose
```

The oracle is the family's; reproduction is declared by the family's `oracle.py`:

| Family | Reproduction signature |
|--------|------------------------|
| `xml`      | good/bad BaseX server pair disagree on the query result (servers started internally) |
| `ffmpeg`   | candidate trips the FFmpeg ASAN build |
| `binutils` | pinned binutils tool dies on the configured `signal` (e.g. SIGSEGV) or emits the `needle` substring |
| `crashjs`  | long-lived `node worker.mjs` reports the configured `(errType, errMsg, topFile)` triple |

## `cherrypick_xml`

Stochastically shrinks an XML file to a target size range while preserving oracle satisfaction. It produced the `predicates/xml/.../input.pick/` seed variants that ship in-tree; those are the canonical paper inputs, so this is rarely needed directly. Regeneration is stochastic — pass `--seed` for a reproducible result.

```
usage: cherrypick_xml <predicate> [--input FILE] [--output FILE]
                      [--min-kb N] [--max-kb N] [--seed N]
                      [--max-attempts N] [--max-consecutive-fails N] [--verbose]

  predicate               path to a case directory (needs query.xq + input; runs before any manifest exists, so the BaseX versions are read from the case dir name and lib/)
  --min-kb                lower bound on output size in KB           (default: 5)
  --max-kb                upper bound on output size in KB           (default: 10)
  --seed                  random seed for reproducibility
  --max-attempts          max node removal attempts                  (default: 100000)
  --max-consecutive-fails stop after N consecutive oracle rejections (default: 50)
```

```bash
cli/cherrypick_xml predicates/xml/cases/case-1e9bc83-1 --input input.xml --output input.pick/1.xml --min-kb 0 --max-kb 1 --verbose
```

## `bench`

Runs the benchmark suite (reducers × families × cases) from an optional JSON spec, writing per-task logs and a summary CSV under `benchmark/runs/`. Every spec field is optional; an omitted field means "all". To reproduce the paper's full table instead, use [benchmark/scripts/drdd_issre.py](../benchmark/scripts/drdd_issre.py).

```jsonc
{
  "reducers": ["ddmin", "probdd"],     // omit -> all five reducers
  "families": {
    "binutils": ["21135", "21139"],    // selected case ids
    "xml": []                          // [] -> all cases of this family
  }                                    // omit "families" -> all families, all cases
}
```

```bash
cli/bench                            # all reducers x all families x all cases
cli/bench spec.json                  # as selected by the spec
cli/bench <(echo '{"families": {"xml": []}}')   # one family, all cases
```

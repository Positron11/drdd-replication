# CLI

Command-line tools for minimization and benchmarking. Both are family-agnostic — they take a family name and work for any of them. Tooling specific to one family lives with that family: the XML seed-variant generator is [`predicates/xml/cherrypick`](../predicates/xml/cherrypick). Run from the repo root with the venv active — after `pip install -e .` the library is on the import path, so no `PYTHONPATH` is needed. If extraction dropped the executable bit, run `chmod +x cli/*` once or invoke via `python cli/<tool>`.

## `minimize`

Minimizes one predicate input with a DD-family reducer. The case is selected from its family's `manifest.json` by id; the input path and oracle config come from the manifest.

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

A family's `tuning` block declares properties of its *inputs* — `p_0`, roughly how removable they are. Each reducer receives a property only if its signature has a parameter for it, so `probdd` and `cdd` get `p_0` and `ddmin`/`drdd` ignore it; see `tuning_for` in [`src/reducers/__init__.py`](../src/reducers/__init__.py). A reducer's own knobs — `drdd`'s `c_iters`, `probdd`'s `seed` — are not input properties and stay out of manifests.


## `bench`

Runs the benchmark suite (reducers × families × cases) from an optional JSON spec, writing per-task logs and a summary CSV under `benchmark/runs/`. Every spec field is optional; an omitted field means "all". To reproduce the paper's full table instead, use [benchmark/scripts/drdd_issre.py](../benchmark/scripts/drdd_issre.py).

```jsonc
{
  "reducers": ["ddmin", "probdd"],     // omit -> all four reducers
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

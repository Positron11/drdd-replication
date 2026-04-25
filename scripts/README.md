# Scripts

CLI tools for minimization and input preparation. Run from the repo root with `PYTHONPATH=src`.

## `minimize_xml`

Minimizes an XML file against a BaseX-backed predicate. Starts a good/bad BaseX server pair internally.

```
usage: minimize_xml <predicate_dir> [--input FILE] [--output FILE]
                    [--algorithm ALGO] [--verbose]

  predicate_dir   path to a predicate directory (must contain config.toml and query.xq)
  --input         input filename within predicate_dir  (default: input.xml)
  --output        output filename within predicate_dir (default: input.min.xml)
  --algorithm     one of: cdd, ddmin, ddprime, pmadd, probdd  (default: ddmin)
  --verbose       print per-step progress
```

```bash
scripts/minimize_xml predicates/xml/ticket-1e9bc83-1 \
    --input input.pick/1.xml --algorithm ddprime --verbose
```

## `minimize_ffmpeg`

Minimizes a binary file against an FFmpeg ASAN predicate. No server setup required.

```
usage: minimize_ffmpeg <predicate_dir> [--input FILE] [--output FILE]
                       [--algorithm ALGO] [--script FILE] [--verbose]

  --input         input filename within predicate_dir  (default: input)
  --output        output filename within predicate_dir (default: input.min)
```

```bash
scripts/minimize_ffmpeg predicates/ffmpeg/ticket-10699 \
    --algorithm pmadd --verbose
```

## `minimize_binutils`

Minimizes a binary file against a binutils crash predicate. The oracle reruns a pinned binutils tool on each candidate and considers the bug reproduced when the process dies on a configured signal (`signal = "SIGSEGV"`) or emits a needle substring in stderr/stdout (`needle = "..."`).

```
usage: minimize_binutils <predicate_dir> [--input FILE] [--output FILE]
                         [--algorithm ALGO] [--verbose]

  --input         input filename within predicate_dir  (default: input)
  --output        output filename within predicate_dir (default: input.min)
```

```bash
scripts/minimize_binutils predicates/binutils/bug-21135 \
    --algorithm ddmin --verbose
```

## `minimize_crashjs`

Minimizes a JavaScript test file against a CrashJS lodash crash predicate. The oracle drives a long-lived `node worker.mjs` process via stdin/stdout pipes; each candidate is written into a sandboxed staging file under `lib/case-staging/` and ESM-cache-busted with a per-call counter. Reproduction is declared when the worker reports the configured `(errType, errMsg, topFile)` triple.

```
usage: minimize_crashjs <predicate_dir> [--input FILE] [--output FILE]
                        [--algorithm ALGO] [--verbose]

  --input         input filename within predicate_dir  (default: input)
  --output        output filename within predicate_dir (default: input.min)
```

```bash
scripts/minimize_crashjs predicates/crashjs/lodash-9 \
    --algorithm ddmin --verbose
```

## `cherrypick_xml`

Stochastically shrinks an XML file to a target size range while preserving oracle satisfaction. Used by `make -C predicates/xml` to generate `input.pick/` variants; rarely needed directly.

```
usage: cherrypick_xml <predicate> [--input FILE] [--output FILE]
                      [--min-kb N] [--max-kb N] [--seed N]
                      [--max-attempts N] [--max-consecutive-fails N] [--verbose]

  predicate               path to a predicate directory (must contain config.toml and query.xq)
  --min-kb                lower bound on output size in KB           (default: 5)
  --max-kb                upper bound on output size in KB           (default: 10)
  --seed                  random seed for reproducibility
  --max-attempts          max node removal attempts                  (default: 100000)
  --max-consecutive-fails stop after N consecutive oracle rejections (default: 50)
```

```bash
scripts/cherrypick_xml predicates/xml/ticket-1e9bc83-1 \
    --input input.xml --output input.pick/1.xml --min-kb 0 --max-kb 1 --verbose
```

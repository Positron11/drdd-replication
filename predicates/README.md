# Predicates

Four families of real-world bug reproducers: [XML](#xml) (15 cases), [FFmpeg](#ffmpeg) (14), [Binutils](#binutils) (12) and [CrashJS](#crashjs) (11). Each predicate is a directory holding the input file(s) needed to reproduce the bug; its run config lives in the family's `manifest.json`.

## Family layout

Each family is a self-contained plugin under `predicates/<name>/`:

| File | Role |
|------|------|
| `manifest.json` | The source of truth — see the contract below. |
| `oracle.py` | Defines the `Oracle` subclass the manifest names: the predicate, built and validated from a resolved config. The filename and class are the manifest's to choose. |
| `cases/` | Per-case data — input files only; configuration lives in the manifest. |
| support modules | Anything the oracle imports, e.g. `xml/basex.py`, `crashjs/session.py`. |

The library auto-discovers any directory holding a `manifest.json` and does what the manifest says: it imports the module the `oracle` field names, takes the class it names, and runs exactly the inputs the `predicates` array lists — an input not listed is skipped. The oracle is imported as a plugin rooted at its family, so its own relative imports (`from .basex import ...`) resolve against its own files. **Adding a family or a case needs no change under [`src/`](../src/).**

### The manifest contract

```jsonc
{
  "name"  : "crashjs",                    // what the family is called (never inferred from the directory)
  "oracle": "oracle.py:CrashJSOracle",    // <module>:<class>, module relative to the family
  "build" : "make",                       // omit when the artifacts ship in-tree, as xml's jars do
  "common": { "timeout": 10 },            // config merged into every case
  "tuning": { "p_0": 0.45 },              // properties of this family's inputs (see below)
  "predicates": [
    {
      "id"    : "9",                             // how the CLIs select this case
      "path"  : "cases/lodash-9/input",          // its input, relative to the family
      "config": { "errType": "TypeError" },      // the oracle's settings; overlays `common`
      "files" : { "query": "cases/x/query.xq" }, // aux paths, resolved and exposed under their own names
      "meta"  : { "url": "https://..." }         // provenance the loader carries but never reads
    }
  ]
}
```

Every path is relative to the family, `build` included: it says only *what* to run, since where to run it is the family's own directory — which a manifest cannot name without hardcoding where it happens to sit. The loader supplies the location, so a family loaded from anywhere reports a command that works. The resolved command reaches every case's config, and an oracle names it when an artifact is missing: `require(path, build=config.get("build"))`.

Nothing is guessed from the layout. The oracle class is named and looked up, rather than the loader importing the module and searching it for whatever happens to subclass `Oracle`, so a family may keep as many classes as it likes.

**The directory and the manifest answer different questions.** The directory is where a family lives and how one is selected — `minimize <family> <case>` resolves a path under `predicates/`. The manifest says what the family is *called*: `name` is read from it, never inferred, so a family's identity travels with its data.

A manifest is hand-edited, so every way one can be malformed — invalid JSON, a missing `name`/`id`/`path`, a duplicate case id, an unresolvable `oracle` ref, a `files` key colliding with a config key — is reported as a `ConfigError` naming the file and the offending entry, rather than crashing or silently dropping a case.

**Case ids.** Each predicate's `id` is how the CLIs select a case (`minimize <family> <id>`, or a benchmark spec's case lists). Ids are the bug/ticket numbers for binutils and ffmpeg, `1`–`11` for crashjs, and `<case>.<variant>` (`1.1`–`5.3`) for the xml size variants.

**Tuning.** The optional `tuning` block names properties of the family's *inputs* — not of any reducer:

```jsonc
"tuning": { "p_0": 0.45 }
```

`p_0` is roughly how removable the inputs are: binutils `0.8`, crashjs `0.45`, xml `0.25`, ffmpeg `0.01`. Each reducer receives a property only if its signature has a parameter for it, so `probdd` and `cdd` read `p_0` and the rest ignore it. The manifest names no reducer, so the pool stays ignorant of the roster; the mapping lives in [`tuning_for`](../src/reducers/__init__.py). A reducer's own knobs — `drdd`'s `c_iters` (the ablation axis), `probdd`'s `seed` (the reproducibility anchor) — are not input properties and stay out of manifests.

**The oracle contract.** [`core.Oracle`](../src/core/oracle.py) counts every call — *oracle calls* is the benchmark's universal cost metric. A family implements `_call`; a stateful one also overrides `__enter__`/`__exit__` to hold servers or subprocesses open across a run.

## XML

Five cases (`case-1e9bc83-{1..5}`) sourced from the artifact of Zhang et al. ("Toward a Better Understanding of Probabilistic Delta Debugging"). Each encodes a query-processing discrepancy between two BaseX versions: the predicate succeeds when an input XML document triggers incorrect output on the bad version (`816b386`) while the good version (`1e9bc83`) remains correct.

**Case layout:**

```
cases/case-1e9bc83-<n>/
  input.xml          — original input
  input.pick/        — pre-shrunk seed variants (variant k ≤ 2k KB)
    1.xml ... 3.xml
  query.xq           — discriminating XQuery
lib/                 — BaseX JARs
manifest.json        — common config + the input paths to benchmark
```

**Seed variants ship in-tree.** The `input.pick/` variants are tracked in the repository and are the exact inputs the paper used, so no build step is needed. They were produced from each `input.xml` by [`xml/cherrypick`](xml/cherrypick) (variant *k* shrunk to ≤ 2*k* KB while preserving the oracle). Regenerating is a provenance exercise only — `cherrypick` removes nodes stochastically, so a fresh run yields *different* inputs and will not match the paper unless you pass a fixed `--seed`. To experiment (requires Java 11+ for the BaseX oracle):

```bash
predicates/xml/cherrypick predicates/xml/cases/case-1e9bc83-1 \
    --input input.xml --output input.pick/1.xml --min-kb 0 --max-kb 2 --seed 0 --verbose
```

```
usage: cherrypick <case-dir> [--input FILE] [--output FILE]
                  [--min-kb N] [--max-kb N] [--seed N]
                  [--max-attempts N] [--max-consecutive-fails N] [--verbose]

  case-dir                a case directory under cases/ (needs query.xq and an input);
                          the BaseX versions come from the case directory name and lib/,
                          and the Oracle class from this family's manifest.json
  --input                 input file, relative to the case dir     (default: input.xml)
  --output                output file, relative to the case dir
  --min-kb                lower bound on output size in KB         (default: 5)
  --max-kb                upper bound on output size in KB         (default: 10)
  --seed                  random seed for reproducibility
  --max-attempts          max node removal attempts                (default: 100000)
  --max-consecutive-fails stop after N consecutive oracle rejections (default: 50)
```

It lives here rather than in [`cli/`](../cli/) because it is this family's: it cannot run against any other. `minimize` and `bench` are family-agnostic; this is not.

## FFmpeg

ASAN-detected bugs across two FFmpeg commits. Each predicate fires when the instrumented binary triggers a sanitizer report on the input file.

| Directory | Filter | FFmpeg Commit |
|-----------|--------|---------------|
| ticket-[10686](https://trac.ffmpeg.org/ticket/10686)/ | `afireqsrc` | [`466799d`](https://github.com/FFmpeg/FFmpeg/commit/466799d4f5) |
| ticket-[10688](https://trac.ffmpeg.org/ticket/10688)/ | `bwdif` | [`466799d`](https://github.com/FFmpeg/FFmpeg/commit/466799d4f5) |
| ticket-[10691](https://trac.ffmpeg.org/ticket/10691)/ | `dialoguenhance` | [`466799d`](https://github.com/FFmpeg/FFmpeg/commit/466799d4f5) |
| ticket-[10699](https://trac.ffmpeg.org/ticket/10699)/ | `blurdetect` | [`466799d`](https://github.com/FFmpeg/FFmpeg/commit/466799d4f5) |
| ticket-[10701](https://trac.ffmpeg.org/ticket/10701)/ | `colorcorrect` | [`466799d`](https://github.com/FFmpeg/FFmpeg/commit/466799d4f5) |
| ticket-[10702](https://trac.ffmpeg.org/ticket/10702)/ | `transpose,gradfun` | [`466799d`](https://github.com/FFmpeg/FFmpeg/commit/466799d4f5) |
| ticket-[10744](https://trac.ffmpeg.org/ticket/10744)/ | `alimiter` | [`8d24a28`](https://github.com/FFmpeg/FFmpeg/commit/8d24a28d06) |
| ticket-[10745](https://trac.ffmpeg.org/ticket/10745)/ | `swaprect` | [`8d24a28`](https://github.com/FFmpeg/FFmpeg/commit/8d24a28d06) |
| ticket-[10746](https://trac.ffmpeg.org/ticket/10746)/ | `stereowiden` | [`8d24a28`](https://github.com/FFmpeg/FFmpeg/commit/8d24a28d06) |
| ticket-[10747](https://trac.ffmpeg.org/ticket/10747)/ | `stereotools` | [`8d24a28`](https://github.com/FFmpeg/FFmpeg/commit/8d24a28d06) |
| ticket-[10749](https://trac.ffmpeg.org/ticket/10749)/ | `showspectrumpic` | [`8d24a28`](https://github.com/FFmpeg/FFmpeg/commit/8d24a28d06) |
| ticket-[10754](https://trac.ffmpeg.org/ticket/10754)/ | `separatefields` | [`8d24a28`](https://github.com/FFmpeg/FFmpeg/commit/8d24a28d06) |
| ticket-[10756](https://trac.ffmpeg.org/ticket/10756)/ | `showwaves` | [`8d24a28`](https://github.com/FFmpeg/FFmpeg/commit/8d24a28d06) |
| ticket-[10758](https://trac.ffmpeg.org/ticket/10758)/ | `minterpolate` | [`8d24a28`](https://github.com/FFmpeg/FFmpeg/commit/8d24a28d06) |

### Build

```bash
make -C predicates/ffmpeg           # build lib/ffmpeg_g-<commit>
```

Clones FFmpeg at each commit, configures with clang and debug symbols, injects `-fsanitize=address`, builds, and leaves `lib/ffmpeg_g-<full-commit-hash>`.

Two deviations from the configure flags in the bug reports:

- **No `--toolchain=clang-asan`**: FFmpeg's configure runs `nm` on an ASAN-compiled test file, causing it to detect `__odr_asan_gen_` as `extern_prefix` and break the link step. ASAN flags are injected into `ffbuild/config.mak` after configure instead.
- **`--disable-x86asm`**: The `clang-asan` preset adds `-DPREFIX` to NASM flags, giving assembly symbols a leading `_` the C linker doesn't expect. The bugs are in C filter code so disabling assembly doesn't affect reproducibility.

### Reproduce

Run from `predicates/ffmpeg/lib/`:

```bash
ASAN_OPTIONS=halt_on_error=1 ./ffmpeg_g-466799d4f5 -y -i ../cases/ticket-10702/input  -filter_complex "transpose,gradfun" /tmp/out.mp4
```

`halt_on_error=1` ensures a non-zero exit on any sanitizer report.

## Binutils

Crash-triggering inputs for GNU binutils tools, sourced from [Feiyang et al.](https://github.com/FreeFlyingSheep/delta-debugging/) artifact. The predicate fires when the target tool dies on a signal (SEGV) or emits a glibc corruption message on the input file.

| Directory | Bug | Tool | Args | Commit |
|-----------|-----|------|------|--------|
| bug-[20605](https://sourceware.org/bugzilla/show_bug.cgi?id=20605)/    | segfault | x86_64-mingw32-objdump | `-x`   | [`2870b1b`](https://sourceware.org/git/?p=binutils-gdb.git;a=commit;h=2870b1ba83fc0e0ee7eadf72d614a7ec4591b169) |
| bug-[21135](https://sourceware.org/bugzilla/show_bug.cgi?id=21135)/    | segfault | aarch64-linux-readelf  | `-zR3` | [`53f7e8e`](https://sourceware.org/git/?p=binutils-gdb.git;a=commit;h=53f7e8ea7fad1fcff1b58f4cbd74e192e0bcbc1d) |
| bug-[21136](https://sourceware.org/bugzilla/show_bug.cgi?id=21136)/    | segfault | aarch64-linux-readelf  | `-da`  | [`53f7e8e`](https://sourceware.org/git/?p=binutils-gdb.git;a=commit;h=53f7e8ea7fad1fcff1b58f4cbd74e192e0bcbc1d) |
| bug-[21138](https://sourceware.org/bugzilla/show_bug.cgi?id=21138)/    | segfault | aarch64-linux-readelf  | `-R6`  | [`53f7e8e`](https://sourceware.org/git/?p=binutils-gdb.git;a=commit;h=53f7e8ea7fad1fcff1b58f4cbd74e192e0bcbc1d) |
| bug-[21139](https://sourceware.org/bugzilla/show_bug.cgi?id=21139)/    | glibc abort (`corrupted top size`) | aarch64-linux-readelf | `-w` | [`53f7e8e`](https://sourceware.org/git/?p=binutils-gdb.git;a=commit;h=53f7e8ea7fad1fcff1b58f4cbd74e192e0bcbc1d) |
| bug-[21143](https://sourceware.org/bugzilla/show_bug.cgi?id=21143)/    | segfault | aarch64-linux-readelf  | `-R6`  | [`53f7e8e`](https://sourceware.org/git/?p=binutils-gdb.git;a=commit;h=53f7e8ea7fad1fcff1b58f4cbd74e192e0bcbc1d) |
| bug-[21144](https://sourceware.org/bugzilla/show_bug.cgi?id=21144)/    | segfault | aarch64-linux-readelf  | `-w`   | [`53f7e8e`](https://sourceware.org/git/?p=binutils-gdb.git;a=commit;h=53f7e8ea7fad1fcff1b58f4cbd74e192e0bcbc1d) |
| bug-[21145](https://sourceware.org/bugzilla/show_bug.cgi?id=21145)/    | segfault | aarch64-linux-readelf  | `-w`   | [`53f7e8e`](https://sourceware.org/git/?p=binutils-gdb.git;a=commit;h=53f7e8ea7fad1fcff1b58f4cbd74e192e0bcbc1d) |
| bug-[21409-1](https://sourceware.org/bugzilla/show_bug.cgi?id=21409)/    | segfault | x86_64-linux-objdump   | `-SD`  | [`a6c21d4`](https://sourceware.org/git/?p=binutils-gdb.git;a=commit;h=a6c21d4a553de184562fd8409a5bcd3f2cc2561a) |
| bug-21409-2/ | segfault | x86_64-linux-objdump   | `-SD`  | [`a6c21d4`](https://sourceware.org/git/?p=binutils-gdb.git;a=commit;h=a6c21d4a553de184562fd8409a5bcd3f2cc2561a) |
| bug-[21414](https://sourceware.org/bugzilla/show_bug.cgi?id=21414)/    | segfault | x86_64-linux-objcopy   | `-Gs`  | [`a6c21d4`](https://sourceware.org/git/?p=binutils-gdb.git;a=commit;h=a6c21d4a553de184562fd8409a5bcd3f2cc2561a) |
| bug-[30886](https://sourceware.org/bugzilla/show_bug.cgi?id=30886)/    | segfault | x86_64-linux-nm        | `-D`   | [`be8e831`](https://sourceware.org/git/?p=binutils-gdb.git;a=commit;h=be8e83130996a5300e15b415ed290de1af910361) |

Four distinct binutils commits are built, each with the `--target` configuration that produces the toolchain variant for that bug. All resulting binaries are native x86_64 — the target triple affects only which object-file formats the tool can parse.

### Build

```bash
make -C predicates/binutils        # clones binutils-gdb, builds all four commits
```

Clones `binutils-gdb.git` once, then for each configured commit checks out the pinned SHA into a dedicated `build-<short>/` directory, configures with the commit's `--target` (plus `--disable-gdb --disable-sim --disable-gprofng --disable-nls` and `MAKEINFO=true` to bypass missing texinfo), and copies the unprefixed `binutils/<tool>` to `lib/<target>-<tool>-<short>`. Builds run sequentially (`.NOTPARALLEL:`) because all four share one clone.

### Reproduce

```bash
./predicates/binutils/lib/aarch64-linux-readelf-53f7e8ea -zR3 predicates/binutils/cases/bug-21135/input   # SIGSEGV
./predicates/binutils/lib/aarch64-linux-readelf-53f7e8ea -w   predicates/binutils/cases/bug-21139/input   # "malloc(): corrupted top size"
./predicates/binutils/lib/x86_64-linux-objdump-a6c21d4a   -SD predicates/binutils/cases/bug-21409-1/input # SIGSEGV
```

## CrashJS

JavaScript crash reproducers from the CrashJS dataset ([Zenodo record 10530515](https://zenodo.org/records/10530515)), specifically the `syntest-collected/lodash` sub-corpus: 11 mocha test files that crash an instrumented build of lodash. The predicate fires when running the candidate test under our long-lived Node worker produces the same `(errType, errMsg, top-lodash-frame)` triple recorded for the bug.

| Directory | Crash | Top frame |
|-----------|-------|-----------|
| lodash-1/  | `TypeError: customizer is not a function` | `.internal/equalArrays.js` |
| lodash-2/  | `TypeError: equalFunc is not a function`  | `.internal/equalArrays.js` |
| lodash-3/  | `TypeError: customizer is not a function` | `.internal/equalArrays.js` |
| lodash-4/  | `TypeError: equalFunc is not a function`  | `.internal/equalArrays.js` |
| lodash-5/  | `TypeError: equalFunc is not a function`  | `.internal/equalArrays.js` |
| lodash-6/  | `TypeError: string.charCodeAt is not a function` | `.internal/stringToPath.js` |
| lodash-7/  | `TypeError: string.charCodeAt is not a function` | `.internal/stringToPath.js` |
| lodash-8/  | `TypeError: iteratee is not a function`   | `transform.js` |
| lodash-9/  | `TypeError: iteratee is not a function`   | `transform.js` |
| lodash-10/ | `TypeError: iteratee is not a function`   | `transform.js` |
| lodash-11/ | `TypeError: iteratee is not a function`   | `transform.js` |

Inputs are JS source (444 B – 2356 B). The original dataset's `require = require('esm')(module)` shim line is stripped during ingestion — modern Node parses the resulting file natively as ESM.

### Build

```bash
make -C predicates/crashjs           # stage worker.mjs + symlink instrumented lodash
```

Requires system `node` (anything modern; tested on Node 22) plus `curl`/`tar` to fetch the dataset. There are no npm dependencies — the worker imports only Node builtins, and the tests import the instrumented lodash by relative path. Symlinks `lib/instrumented` to the `crashjs/syntest-collected/lodash/instrumented/` checkout so the test files' `import "../instrumented/lodash/..."` paths resolve.

### Reproduce

```bash
cd predicates/crashjs/lib
echo "$PWD/../cases/lodash-9/input" | node worker.mjs
# {"ready":true}
# {"ok":false,"errType":"TypeError","errMsg":"iteratee is not a function","topFile":"transform.js"}
```

The mocha-free [worker](crashjs/worker.mjs) reads test paths from stdin one per line, uses ESM cache-busting (`?t=<counter>`) to pick up in-place mutations, and emits one JSON result line per request. Lodash modules stay cached across calls — only the test file is reloaded.


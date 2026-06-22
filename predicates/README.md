# Predicates

Four families of real-world bug reproducers. Each predicate is a directory holding the input file(s) needed to reproduce the bug; its run config lives in the family's `manifest.json`.

## Family layout

Each family is a self-contained plugin: `predicates/<name>/` holds an `oracle.py` that defines a single `Oracle` subclass (its predicate, built and validated from a resolved config), a `manifest.json` (a `common` config block plus an array of predicates, each carrying an `id`, an input path relative to the family directory like `cases/<case>/...`, and its config), any support modules it needs (e.g. `xml/basex.py`, `crashjs/session.py`), and a `cases/` directory holding the per-case data (just input files — config lives in the manifest). The library auto-discovers any directory containing both an `oracle.py` and a `manifest.json`, loads the oracle as a plugin (so its own `from .basex import ...` relative imports resolve), and the benchmark runs exactly the inputs its `manifest.json` lists (an input not listed is skipped) — adding a family or case needs no changes under `src/`.

Each predicate's `id` is how the CLIs select a case (`minimize <family> <id>`, or a benchmark spec's case lists). Ids are the bug/ticket numbers for binutils and ffmpeg, `1`..`11` for crashjs, and `<case>.<variant>` (`1.1`..`5.3`) for the xml size variants.

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

**Regenerate seed variants** (requires Java 11+):

```bash
make -C predicates/xml clean     # remove all input.pick/ dirs
make -C predicates/xml           # all 5 cases × 3 variants
```

## FFmpeg

ASAN-detected bugs across two FFmpeg commits. Each predicate fires when the instrumented binary triggers a sanitizer report on the input file.

| Directory | Filter | FFmpeg Commit |
|-----------|--------|---------------|
| ticket-[10686](https://trac.ffmpeg.org/ticket/10686)/ | `afireqsrc` | [`466799d`](https://github.com/FFmpeg/FFmpeg/commit/466799d4f5) |
| ticket-[10688](https://trac.ffmpeg.org/ticket/10688)/ | `bwdif` | [`466799d`](https://github.com/FFmpeg/FFmpeg/commit/466799d4f5) |
| ticket-[10691](https://trac.ffmpeg.org/ticket/10691)/ | `dialoguenhance` | [`466799d`](https://github.com/FFmpeg/FFmpeg/commit/466799d4f5) |
| ticket-[10699](https://trac.ffmpeg.org/ticket/10699)/ | `blurdetect` | [`466799d`](https://github.com/FFmpeg/FFmpeg/commit/466799d4f5) |
| ticket-[10700](https://trac.ffmpeg.org/ticket/10700)/ | `afwtdn` | [`466799d`](https://github.com/FFmpeg/FFmpeg/commit/466799d4f5) |
| ticket-[10701](https://trac.ffmpeg.org/ticket/10701)/ | `colorcorrect` | [`466799d`](https://github.com/FFmpeg/FFmpeg/commit/466799d4f5) |
| ticket-[10702](https://trac.ffmpeg.org/ticket/10702)/ | `transpose,gradfun` | [`466799d`](https://github.com/FFmpeg/FFmpeg/commit/466799d4f5) |
| ticket-[10743](https://trac.ffmpeg.org/ticket/10743)/ | `doubleweave` | [`8d24a28`](https://github.com/FFmpeg/FFmpeg/commit/8d24a28d06) |
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

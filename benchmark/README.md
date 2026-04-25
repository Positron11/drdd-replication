# Benchmark Suite

Runs all five algorithms against XML, FFmpeg, binutils, and CrashJS predicates and writes a timestamped CSV per run.

## XML

Requires Java 11+ and `nc`.

```bash
python benchmark/scripts/bench_xml.py
```

Discovers all `ticket-*` cases under `predicates/xml/`, runs every algorithm × every input variant (1–3), and writes results under `benchmark/runs/`.

Seed inputs (`input.pick/1.xml` … `3.xml`) are already checked in. Regenerate them when predicate inputs change:

```bash
make -C predicates/xml clean     # remove all input.pick/ dirs
make -C predicates/xml           # build all missing variants
```

## FFmpeg

```bash
python benchmark/scripts/bench_ffmpeg.py
```

Discovers all `ticket-*` cases under `predicates/ffmpeg/` (excluding `x-ticket-*`), runs every algorithm against each case's `input` binary. No server setup required.

Requires `predicates/ffmpeg/lib/ffmpeg_g`. Build it first if missing:

```bash
make -C predicates/ffmpeg
```

## Binutils

```bash
python benchmark/scripts/bench_binutils.py
```

Discovers all `bug-*` cases under `predicates/binutils/`, runs every algorithm against each case's `input` binary. The oracle runs a pinned binutils tool on the candidate and declares reproduction on either a signal (SEGV) or a configured substring in stderr.

Requires `predicates/binutils/lib/aarch64-linux-readelf-53f7e8ea`. Build it first if missing:

```bash
make -C predicates/binutils
```

## CrashJS

```bash
python benchmark/scripts/bench_crashjs.py
```

Discovers all `lodash-*` cases under `predicates/crashjs/`, runs every algorithm against each case's `input` test file. The oracle drives a long-lived `node worker.mjs` process and matches reproductions against the configured `(errType, errMsg, topFile)` signature.

Requires `predicates/crashjs/lib/node_modules/` and a system `node` binary. Build first if missing:

```bash
make -C predicates/crashjs
```

## Output

Each run creates a directory under `benchmark/runs/` named `<label>_<DD-MM-YYYY>_<HH:MM>_git-<sha>/` containing:

| File | Contents |
|------|----------|
| `result.csv` | Per-task metrics |
| `logs/<n>_<predicate>_<algo>.log` | Full minimization trace |

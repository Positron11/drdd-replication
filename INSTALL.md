# Installation

Prerequisites are in [`REQUIREMENTS.md`](REQUIREMENTS.md). Full usage, and the
mapping from each paper table to the command that regenerates it, is in the
[README](README.md) — this file covers installation and the basic functionality
check only.

## Option A — container (recommended)

Freezes the whole environment and bakes in all four oracle libraries at build
time, so none of the host toolchain is needed. Standard OCI; Podman and Docker
take identical commands.

```bash
podman build -t drdd .        # or: docker build -t drdd .
```

The build clones binutils-gdb and FFmpeg and compiles an AddressSanitizer FFmpeg,
so it needs network access and roughly 30–60 minutes the first time; the image is
several GB.

Then, to check it works:

```bash
podman run --rm drdd cli/minimize crashjs 9 --reducer drdd --verbose
```

## Option B — native

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .              # installs the dependencies and the library
```

Run every command from the repository root with the venv active — the tools use
repo-root-relative paths, and the editable install puts the library packages
(`reducers`, `loader`, `bench`, …) on the import path so no `PYTHONPATH` is
needed.

> **Executable permissions.** The `cli/*` scripts ship with the executable bit
> set, but some archive tools (notably `unzip`) drop it on extraction. If you get
> `Permission denied`, restore it once with `chmod +x cli/*`, or invoke via
> `python cli/<tool>`.

### Building the oracles

Each family builds its oracle from upstream source. Build only what you intend to
run; a family whose oracle is missing is reported and skipped, so the rest still
run.

```bash
make -C predicates/crashjs     # node, curl, tar        — fastest
make -C predicates/binutils    # gcc, flex, bison, m4
make -C predicates/ffmpeg      # clang + compiler-rt    — slowest
```

XML needs no build: its BaseX jars and seed inputs ship in-tree, and it needs
only a JRE at run time.

> **Binutils gotcha.** Without `flex`/`bison`/`m4` the build fails with
> `Error 127`. An interrupted build can leave a stale `config.cache` that causes
> a later `"YACC has changed since the previous run"` error — recover with
> `rm -rf predicates/binutils/build/build-*` and rebuild.

## Basic functionality check

XML needs no build — its BaseX jars and inputs ship in-tree — so it is the
quickest confirmation that the install is sound (it needs a JRE):

```bash
cli/bench <(echo '{"reducers":["drdd"],"families":{"xml":["1.1"]}}')
```

Or, once a built family is available, confirm one case end to end:

```bash
make -C predicates/crashjs
cli/minimize crashjs 9 --reducer drdd --verbose    # expect 217 B in 982 oracle calls
```

Either exercises the whole pipeline — manifest loading, oracle construction, the
reducer, and the runner's safety net, which re-checks that the minimized output
still reproduces before returning it.

Then see [README.md](README.md) for the full reproduction.

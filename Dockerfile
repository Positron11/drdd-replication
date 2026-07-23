# Self-contained reproduction image for the Dr. DD replication package.
#
# Bakes all four predicate-family oracles in at build time, so the paper's
# tables can be regenerated in a fixed environment, offline. The file is a
# standard Dockerfile and builds with either Podman or Docker.
#
#   podman build -t drdd .                                       # or: docker build -t drdd .
#   podman run --rm -it drdd                                     # shell in the artifact
#   podman run --rm drdd python benchmark/scripts/drdd_issre.py  # regenerate the main table
#
# The build clones binutils-gdb and FFmpeg and compiles an AddressSanitizer
# FFmpeg from source, so it needs network access and roughly 30-60 minutes the
# first time; the resulting image is a few GB.
#
# Two runtime caveats that a build cannot freeze, both documented in README.txt
# section 8: binutils case 21409-2 is ASLR-sensitive (the container shares the
# host's ASLR), and the ASan FFmpeg may need `vm.mmap_rnd_bits=28` set on the
# host if it cannot map its shadow memory.

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# One toolchain layer covering every family:
#
#   python3             # the runner, the probdd reducer (numpy), the xml driver
#   default-jre         # BaseX servers for the xml oracle (its jars ship in-tree)
#   clang               # builds the AddressSanitizer FFmpeg
#   libclang-rt-18-dev  # provides libclang_rt.asan*.a, which the ASan link needs
#   gcc flex bison m4   # builds binutils (it generates lexers/parsers)
#   file                # binutils' libtool probes binary types with it; without
#                       #   it, libtool falls back and the configure step is noisy
#   git curl tar make   # fetch and build the upstream oracle sources

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates git curl tar xz-utils make file \
        python3 python3-pip python3-venv \
        default-jre-headless \
        clang libclang-rt-18-dev \
		gcc g++ flex bison m4 \
	&& rm -rf /var/lib/apt/lists/*

# Python deps in an isolated venv (sidesteps Ubuntu's PEP 668 lock and keeps the
# environment explicit). pyproject.toml pins defusedxml, saxonche, numpy.

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /artifact
COPY . /artifact
RUN pip install --no-cache-dir -e .

# Restore the executable bit on every entry point. COPY carries whatever the
# build context had, and some archive tools (e.g. unzip) drop it on extraction —
# which would make the documented `cli/minimize ...` calls fail with
# "Permission denied" inside the container. predicates/xml/cherrypick is the
# XML family's own seed-variant generator.
RUN chmod +x cli/minimize cli/bench predicates/xml/cherrypick

# Fail fast. Import the library and resolve all four family manifests and their
# oracle plugins (which also imports saxonche for xml) before the slow oracle
# builds below - so a broken package or manifest surfaces in seconds, not after
# half an hour of compilation. Constructing an oracle needs its built binary;
# loading a family does not, so this runs here safely.
RUN python -c "from pathlib import Path; from loader import load_family; \
	[load_family(Path('predicates')/f) for f in ('xml','ffmpeg','binutils','crashjs')]; \
	print('library + all four manifests OK')"

# Build the three oracle libs that are not shipped prebuilt (xml ships its BaseX
# jars in-tree and needs no build), one layer each so a failure in a later family
# doesn't re-run the earlier (slow) builds. Each drops its build tree in the SAME
# RUN — deleting it in a later layer wouldn't shrink the image, since the data
# would still sit in the lower layer.

RUN make -C predicates/binutils && rm -rf predicates/binutils/build
RUN make -C predicates/ffmpeg   && rm -rf predicates/ffmpeg/build

# Node 22 for the crashjs worker (Ubuntu's default Node 18 makes the oracle
# inconsistent). Installed here, before the crashjs build: its Makefile checks
# for node on PATH. binutils/ffmpeg above don't need it, so they stay cached.

RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
	&& apt-get install -y --no-install-recommends nodejs \
	&& rm -rf /var/lib/apt/lists/*

# crashjs/lib/instrumented is a symlink into build/ (the full downloaded dataset),
# so turn it into real files before dropping build/ — keeping only the
# instrumented-lodash tree the oracle needs, not the whole dataset + tarball.

RUN make -C predicates/crashjs \
	&& cp -rL predicates/crashjs/lib/instrumented predicates/crashjs/lib/instrumented.real \
	&& rm predicates/crashjs/lib/instrumented \
	&& mv predicates/crashjs/lib/instrumented.real predicates/crashjs/lib/instrumented \
	&& rm -rf predicates/crashjs/build

# No PYTHONPATH needed: `pip install -e .` above put the library on the import
# path, so the same commands work here as in a host venv.
CMD ["/bin/bash"]

# Requirements

Hardware and software needed to run this artifact. Installation steps are in
[`INSTALL.md`](INSTALL.md); the badges claimed and how reproduction is checked are in [`README.txt`](README.txt).

## Hardware

| | |
|---|---|
| Architecture | x86_64 |
| Disk | ~10 GB free (the binutils and FFmpeg builds clone large upstream repositories) |
| Memory | 8 GB is comfortable; the reference runs used 64 GB |
| Network | Required at build time only — each family's `Makefile` fetches upstream sources. The container image, once built, runs offline. |

The paper's reference figures were measured on Fedora Linux x86_64, AMD Ryzen,
64 GB RAM, with 2 pinned cores. A full four-family reproduction takes **~11 hours**
on that setup.

## Software

The recommended path is the bundled [`Dockerfile`](Dockerfile), which freezes
everything below and bakes in all four oracle libraries. It builds with Podman or
Docker and needs none of the host toolchain.

Running natively instead requires:

| | Needed for |
|---|---|
| Linux, x86_64 | everything |
| Python ≥ 3.11 | the library and all tooling |
| `clang` + compiler-rt (`libclang-rt-*-dev`) | building the AddressSanitizer FFmpeg |
| `gcc`, `flex`, `bison`, `m4` | building binutils (it generates lexers and parsers) |
| `node` (tested on 22), `curl`, `tar` | the CrashJS worker and dataset fetch |
| Java 11+ (JRE is enough) | the XML family's BaseX servers at run time |
| `git`, `make` | fetching and building the upstream oracle sources |

Python dependencies (`defusedxml`, `saxonche`, `numpy`) are declared in
[`pyproject.toml`](pyproject.toml) and installed by `pip install -e .`.

## Running only part of it

Nothing above is all-or-nothing — build only the families you intend to run, and
a family whose oracle is missing is reported and skipped so the rest still run.

| Want to run | Needs |
|---|---|
| XML | Python and a JRE — its BaseX jars ship in-tree, so there is no build step |
| CrashJS | `node`, `curl`, `tar` — the fastest of the built families |
| Binutils | `gcc`, `flex`, `bison`, `m4`, and time for the build |
| FFmpeg | `clang` + compiler-rt, and the largest build of the four |

XML is the cheapest way to confirm the package works, since it needs no build at
all; CrashJS is the fastest to actually run once built.

## Known environmental caveat

The FFmpeg oracle is an AddressSanitizer build. On some recent kernels ASan
cannot map its shadow memory under high-entropy ASLR; if the FFmpeg family aborts
at startup with an ASan mmap/shadow-memory message, lower the host setting once
with `sudo sysctl -w vm.mmap_rnd_bits=28` and re-run. A container shares the host
kernel, so this is set on the host, not in the image.

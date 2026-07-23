================================================================================
ISSRE 2026 ARTIFACT -- Dr. DD: 1-Minimal Isolation of Failure Causes via
                       Deferred Restarts
================================================================================

This file is the artifact's entry point and follows the structure required by
the ISSRE 2026 Call for Artifacts. It is self-contained; nothing here
depends on reading any other file. README.md is the repository landing page
(orientation and a documentation map).


--------------------------------------------------------------------------------
1. TARGET CATEGORY
--------------------------------------------------------------------------------

Code and Dataset.

Code:    implementations of the four Delta Debugging algorithms the paper
         evaluates, the oracle/predicate framework they run against, the
         benchmark harness, and the three experiment scripts that regenerate
         the paper's tables.

Dataset: 52 real-world bug-reproducing inputs across four subject families
         (XML, FFmpeg, binutils, CrashJS), all shipped in-tree, together with
         the manifests recording each case's provenance and run configuration.

The oracle binaries themselves are not shipped -- they are built from pinned
upstream sources by each family's Makefile, or baked into the container image.


--------------------------------------------------------------------------------
2. TARGET BADGE
--------------------------------------------------------------------------------

Reproducible (and therefore also Available and Reviewed).

Available    The artifact is archived at
             https://doi.org/10.5281/zenodo.21498483 under the MIT License
             (see LICENSE). It is self-contained: all source, all predicate
             inputs, and all build recipes are included.

Reviewed     Every component documented here is runnable as documented.
             Section 7 gives a functionality check that needs no compilation
             and completes in well under a minute.

Reproducible Section 8 regenerates the paper's per-case results. The three
             deterministic reducers (ddmin, cdd, drdd) reproduce their
             reported (minimized_length, oracle_invocations) pairs exactly.
             Every result.csv records the SHA-256 of each input it consumed,
             so a reproduction carries proof it ran on the shipped data. Two
             narrow, documented exceptions are listed in section 8.


--------------------------------------------------------------------------------
3. INFO
--------------------------------------------------------------------------------

Paper title:   Dr. DD: 1-Minimal Isolation of Failure Causes via Deferred
               Restarts

Submission ID: 238

Venue:         The 37th International Symposium on Software Reliability
               Engineering (ISSRE 2026), Research Track

Authors:

  Aarush Kumbhakern *          Ashoka University, India
                               aarush.kumbhakern_ug25@ashoka.edu.in

  Feiyang Chen                 University of Sydney, Australia
                               fche0060@uni.sydney.edu.au

  Danushka Liyanage *          University of Sydney, Australia
                               danushka.liyanage@sydney.edu.au

  Xi Wu *                      University of Sydney, Australia
                               xi.wu@sydney.edu.au

  Mohammad Amin Alipour *      University of Houston, USA
                               maalipou@central.uh.edu

  Rahul Gopinath *             University of Sydney, Australia
                               rahul.gopinath@sydney.edu.au

  * corresponding author


--------------------------------------------------------------------------------
4. EXPECTED BEHAVIOUR
--------------------------------------------------------------------------------

Delta Debugging shrinks a failure-inducing input to a smaller one that still
fails. The paper's contribution, Dr. DD (`drdd` in this code), reaches a
1-minimal result -- one where no single remaining element can be removed
without losing the failure -- using substantially fewer oracle queries than
the classical ddmin baseline, while the efficient competitors ProbDD and CDD
reach their speed by giving up 1-minimality.

The artifact lets a reviewer confirm exactly that:

  (a) Run any of the four reducers against any of the 52 subjects, and see the
      minimized output size and the number of oracle calls it cost.

  (b) Check 1-minimality directly rather than taking a reducer's word for it.
      `causal_chain_scan` drives a single-element sweep to a fixed point
      against a fresh oracle; whatever it still removes is what the reducer
      left behind. This is the measurement behind the paper's Table IV.

  (c) Regenerate the paper's tables and compare against the reported figures.

Concretely, on CrashJS case 9 (a 444-byte input), drdd reaches a 1-minimal
217 bytes in 982 oracle calls where ddmin needs 8,493 -- about 12% of the
cost. Both outputs are 1-minimal; they differ slightly in size because
1-minimality is a local property, so distinct local minima need not be equal.

Every reducer treats its input as an opaque byte sequence and knows nothing
about the format, so results are not the product of format-specific tricks.


--------------------------------------------------------------------------------
5. ARTIFACT DESCRIPTION
--------------------------------------------------------------------------------

  README.txt         This file.
  README.md          Repository landing page: orientation and a doc map.
  INSTALL.md         Installation, both container and native.
  REQUIREMENTS.md    Hardware and software prerequisites, per family.
  LICENSE            MIT.
  Dockerfile         Reproduction image; bakes in all four oracles.
  Makefile           `make dist` packages the tracked file set; `make help`.
  pyproject.toml     Python package metadata and dependencies.

  src/               The installable, family-agnostic library.
    core/            Oracle contract, config, error model, logging.
    reducers/        The four algorithms, one module each, plus the registry.
                     ddmin.py, drdd.py, probdd.py, cdd.py
    loader/          Resolves a predicate family directory into a Family of
                     Cases by reading its manifest.json.
    runtime/         Runs one reducer against one oracle; asserts the result
                     still reproduces before returning it.
    bench/           The benchmark harness, run schema and CSV writer.
    utils/           Formatting and CLI helpers.

  predicates/        The subjects. Each family is a self-contained plugin:
    binutils/        12 cases -- SIGSEGV / heap corruption in readelf,
                     objdump, objcopy, nm at four pinned commits.
    crashjs/         11 cases -- TypeError in an instrumented lodash build.
    ffmpeg/          14 cases -- AddressSanitizer reports under single filters
                     at two pinned commits.
    xml/             15 cases -- XQuery result discrepancy between two BaseX
                     versions (5 documents x 3 size variants).
                     Also holds `cherrypick`, the generator that produced the
                     shipped size variants.
    Each family directory holds manifest.json (the contract: the Oracle class
    it uses, its build command, its cases and their config), oracle.py,
    cases/ (inputs only), and a Makefile where a build is needed.
    predicates/README.md documents the manifest schema in full.

  cli/               minimize -- reduce one case with one reducer.
                     bench    -- run a spec-selected matrix, writing a CSV.

  benchmark/
    scripts/         drdd_issre.py         the main table
                     ablate_drdd.py        the restart-budget study
                     verify_competitors.py the 1-minimality shortfall study
                     _common.py            shared helpers
    specs/reduced.json   the time-budgeted subset used in section 8
    runs/            output directory (created on first run)

Adding a subject or a whole new family requires no change under src/: the
loader discovers any directory holding a manifest.json and does what the
manifest says.


--------------------------------------------------------------------------------
6. ENVIRONMENT SETUP
--------------------------------------------------------------------------------

OS / architecture
    Linux, x86_64. The oracles are native binaries built from upstream C
    sources; no other platform is supported.

CPU
    Any x86_64 processor. 2 cores are sufficient -- the harness is
    single-threaded by design, so that oracle-call counts and timings are not
    perturbed by parallelism. More cores speed up the oracle *builds* only.

RAM
    8 GB minimum, 16 GB recommended. The AddressSanitizer FFmpeg build is the
    memory-hungry component, both to compile and to run.

Disk
    ~15 GB free for a native setup (the binutils and FFmpeg builds clone large
    upstream repositories). ~8 GB for the container image.

Network
    Required at setup time only: each family's Makefile fetches pinned
    upstream sources. Once built, everything runs offline.

Software -- container route (recommended)
    Podman or Docker. Nothing else; the image carries Python, Java, clang,
    the binutils toolchain and Node, and bakes in all four oracles.

Software -- native route
    Python >= 3.11                            the library and all tooling
    Java 11+ (JRE)                            the XML family's BaseX servers
    clang + compiler-rt (libclang-rt-*-dev)   the AddressSanitizer FFmpeg
    gcc, flex, bison, m4                      binutils (it generates parsers)
    node (tested on 22), curl, tar            the CrashJS worker and dataset
    git, make                                 fetching and building sources

    Python dependencies (defusedxml, saxonche, numpy) are declared in
    pyproject.toml and installed by `pip install -e .`.

Nothing is all-or-nothing: build only the families you intend to run. A family
whose oracle is missing is reported and skipped, and the rest still run. XML
needs no build at all -- its BaseX jars ship in-tree.

Reference platform for the figures reported in the paper: Fedora Linux 43
(kernel 6.19, x86_64) on an AMD Ryzen AI 9 HX PRO 370 workstation with 64 GB of
RAM, driven by Python 3.14 in a standard virtual environment, with each task
run sequentially on a single core.

Known environment caveat: the FFmpeg oracle is an AddressSanitizer build. On
some recent kernels ASan cannot map its shadow memory under high-entropy
ASLR. If the FFmpeg family aborts at startup with an ASan mmap or
shadow-memory message, set `sudo sysctl -w vm.mmap_rnd_bits=28` once on the
host and re-run. A container shares the host kernel, so this is a host
setting, not an image one.


--------------------------------------------------------------------------------
7. GETTING STARTED
--------------------------------------------------------------------------------

Total time: under two minutes -- about 10 seconds to install, about 70 seconds
to run. No compilation, no toolchain, no downloads beyond the three Python
dependencies.

The XML family is used here precisely because it needs no build step: its
BaseX jars and inputs ship in the artifact, so it exercises the entire
pipeline -- manifest loading, oracle construction, reduction, and the runner's
check that the result still reproduces -- with only a JRE.

  Step 1: install

      python3 -m venv .venv
      source .venv/bin/activate
      pip install -e .

  Step 2: confirm the artifact works (about 70 seconds)

      cli/bench benchmark/specs/getting-started.json

  Expected output: a run directory is created under benchmark/runs/, the two
  tasks report "Completed 2 task(s) (0 failed)", and its result.csv contains:

      predicate  reducer  minimized_length  oracle_invocations
      1.1        ddmin    396               32567
      1.1        drdd     401               1618

  These are not illustrative numbers. They are row T-1e9bc83-1-1 of the
  paper's Table II, reproduced exactly -- both the reduced size and the oracle
  count, for both reducers. So the functionality check is also, on one
  subject, a reproduction check: if these four numbers match, the artifact is
  running the same algorithms over the same input as the paper.

  It is also the paper's claim in miniature. From a 1,391-byte input drdd
  reaches a 1-minimal result in 1,618 oracle calls where ddmin needs 32,567 --
  4.97% of the cost, the figure Table III reports for this row.

  Note that drdd's output is slightly *larger* here (401 b vs 396 b), as the
  paper's own table shows. That is expected and is not a defect: 1-minimality
  is a local property, so two distinct local minima need not be the same size,
  and neither dominates the other. The paper claims a cost advantage at equal
  reduction quality, not the globally smallest output -- which delta debugging
  does not promise. On CrashJS case 9, the ordering reverses: drdd's 217 b is
  smaller than ddmin's 226 b.

If instead you are using the container, the equivalent is:

      podman build -t drdd .        # 30-60 min, builds all four oracles
      podman run --rm drdd cli/bench benchmark/specs/getting-started.json

  Note that the image build itself substantially exceeds the 30-minute
  guidance; the native route above is the fast path for a functionality check.

Troubleshooting

  "Permission denied" running cli/minimize or cli/bench
      Some archive tools drop the executable bit. Run `chmod +x cli/*` once,
      or invoke as `python cli/bench ...`.

  "java: command not found" or a BaseX startup error
      The XML oracle needs a JRE (Java 11+) on PATH.

  A ConfigError naming a manifest file and entry
      The manifest is malformed. The message names the file and the offending
      case; this is the intended behaviour, not a crash.


--------------------------------------------------------------------------------
8. REPRODUCIBILITY
--------------------------------------------------------------------------------

The paper's results are per-case pairs of (minimized_length,
oracle_invocations) for four reducers over 52 subjects, plus two supplementary
studies. Reproduction is offered at two scales.

8.1 REDUCED REPRODUCTION -- about 2.5 hours of compute, plus build time

    Covers all four families and all four reducers, so every claim in the
    paper is exercised on every subject family. Coverage is reduced; the claim
    structure is not.

        make -C predicates/crashjs        # ~2 min
        make -C predicates/binutils       # ~20 min
        make -C predicates/ffmpeg         # ~30 min
        cli/bench benchmark/specs/reduced.json

    156 tasks: binutils and CrashJS complete, 11 of 14 FFmpeg cases, and the
    smallest size variant of each of the 5 XML documents.

    What is omitted, and why: FFmpeg cases 10701, 10745 and 10758 cost 55, 134
    and 109 minutes respectively across the four reducers -- 91% of that
    family's total -- and XML size variants 2 and 3 roughly quadruple that
    family's cost. Both omissions are wall-clock only; nothing about those
    cases is different in kind. benchmark/specs/reduced.json records the same
    rationale.

8.2 FULL REPRODUCTION -- about 10 hours of compute, plus build time

        python benchmark/scripts/drdd_issre.py     # the main table
        python benchmark/scripts/ablate_drdd.py    # the restart-budget study
        python benchmark/scripts/verify_competitors.py

    All 52 subjects x 4 reducers. Measured cost by family, for all four
    reducers: FFmpeg 5.4h, XML 3.4h, binutils 0.9h, CrashJS 0.2h.

    A family whose oracle has not been built is reported and skipped, so the
    remaining families still run.

8.3 CHECKING A REPRODUCTION

    Each run writes benchmark/runs/<family>_<date>_git-<sha>/ containing
    result.csv and a full per-task log. Compare result.csv against the paper's
    tables on (predicate, reducer):

        minimized_length     the reduced output size
        oracle_invocations   the cost metric
        input_sha256         proof of which input produced the row

    ddmin, cdd and drdd are deterministic and should match the reported pairs
    exactly.

    Two documented exceptions, neither affecting any conclusion:

    ProbDD is probabilistic. Its RNG seed is fixed at 0, so it re-runs
    identically on a given host; across hosts, NumPy RNG and floating-point
    differences can shift its counts. Treat its rows as indicative.

    Binutils case 21409-2 is address-space-layout sensitive. Its oracle detects
    the bug as a SIGSEGV from a borderline out-of-bounds access in `objdump -SD`
    that faults only under some memory layouts. Three consequences, all expected
    and none affecting a conclusion:

      - ddmin and drdd reproduce this case: their outputs fault under
        essentially every layout, so their reduced size is stable and their
        oracle-call count moves by only a few between runs (we observed +2 and
        +3 against the paper).

      - probdd and cdd may instead FAIL this one case, reporting "minimized
        output no longer reproduces the predicate" with no row in result.csv.
        This is not a defect: these reducers drive the input to the very edge of
        where the access still faults, and the runner's final, uncounted
        re-check of the result then happens to run under a layout where it does
        not. The reduction itself tracks the paper (it reached the paper's exact
        2,353 oracle calls before the re-check); only the safety-net
        verification is layout-sensitive. A re-run may pass, or produce a row a
        few bytes off the reported one.

      - The pinned-layout alternative. Running the oracle under `setarch -R`
        (ASLR disabled) makes the case fully deterministic, including for probdd
        and cdd. We leave it unpinned so the run matches the conditions the
        paper's figures were measured under; a reviewer who prefers a
        deterministic 21409-2 can prepend `setarch -R` to the command in
        predicates/binutils/oracle.py (inside a container this also needs
        `--security-opt seccomp=unconfined`, as the default profile blocks the
        personality(ADDR_NO_RANDOMIZE) syscall it uses).

    This is the single case out of 52 that does not reproduce cell-for-cell; the
    other 51 reproduce their deterministic (size, oracle-call) pairs exactly.

8.4 THE SUPPLEMENTARY STUDIES

    ablate_drdd.py sweeps drdd's restart budget R and records the resulting
    cost, output size and 1-minimality. R = 1 is a single linear pass; R = |I|
    resolves causal chains to a fixed point and is 1-minimal.

    verify_competitors.py regenerates each competitor's output and drives the
    single-element fixed-point scan over it. Whatever comes off is what the
    competitor left behind -- the paper's non-1-minimality result.

    Both accept a smaller subject set by editing SUBJECTS at the top of the
    script, if their default sets exceed the time available.


--------------------------------------------------------------------------------
LICENSE
--------------------------------------------------------------------------------

MIT -- see the LICENSE file.

The predicate subjects derive from public datasets and bug trackers, cited per
family in predicates/README.md: XML from the artifact of Zhang et al.; FFmpeg
from FFmpeg trac tickets at pinned commits; binutils from the sourceware
Bugzilla via the artifact of Feiyang et al.; CrashJS from the CrashJS dataset
(Zenodo record 10530515). These are citations of others' work.

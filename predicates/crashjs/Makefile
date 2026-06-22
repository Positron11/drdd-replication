# Self-contained setup for the CrashJS lodash predicates.
#
# Downloads the CrashJS dataset (instrumented lodash tree) and stages the
# mocha-free worker into lib/. The worker imports only Node builtins and the
# tests import the instrumented lodash by relative path, so there are no npm
# dependencies. Like the other predicate Makefiles, nothing under lib/ or
# build/ is tracked; worker.mjs is the tracked source and this wires it up.
#
# Requires system `node`, `curl`, and `tar` (does not install them).

DATASET_URL := https://zenodo.org/records/10530515/files/crashjs.tar.gz?download=1
SRCDIR      := build
LIB         := lib
DATASET     := $(SRCDIR)/crashjs/syntest-collected/lodash/instrumented

.PHONY: all clean distclean check-tools

all: $(LIB)/worker.mjs $(LIB)/instrumented

check-tools:
	@for t in node curl tar; do \
		command -v $$t >/dev/null 2>&1 || { echo "error: $$t not found on PATH" >&2; exit 1; }; \
	done

$(LIB):
	mkdir -p $(LIB)

# mocha-free worker (staged from the tracked worker.mjs source)
$(LIB)/worker.mjs: worker.mjs | $(LIB)
	cp $< $@

# dataset: download + extract the instrumented lodash tree
$(SRCDIR)/.extracted: | check-tools
	mkdir -p $(SRCDIR)
	curl -L --fail -o $(SRCDIR)/crashjs.tar.gz "$(DATASET_URL)"
	tar -xzf $(SRCDIR)/crashjs.tar.gz -C $(SRCDIR)
	touch $@

$(LIB)/instrumented: $(SRCDIR)/.extracted | $(LIB)
	@test -d $(DATASET) || { echo "error: dataset not found at $(DATASET) after extract" >&2; exit 1; }
	ln -sfn $(abspath $(DATASET)) $@

clean:
	rm -rf $(LIB)

distclean: clean
	rm -rf $(SRCDIR)

# Sandboxed install of mocha-free worker deps + symlink to instrumented lodash tree.
#
# Requires system `node` and `npm` (does not install or modify them).
# Everything else lives under lib/ and is removed by `make clean`.

LIB         := lib
DATASET     := ../../crashjs/syntest-collected/lodash/instrumented

.PHONY: all clean distclean check-tools

all: $(LIB)/node_modules $(LIB)/instrumented

check-tools:
	@command -v node >/dev/null || { echo "error: node not found on PATH" >&2; exit 1; }
	@command -v npm  >/dev/null || { echo "error: npm not found on PATH"  >&2; exit 1; }

$(LIB)/node_modules: $(LIB)/package.json | check-tools
	cd $(LIB) && npm install --no-audit --no-fund --prefer-offline

$(LIB)/instrumented:
	@if [ ! -d $(DATASET) ]; then \
		echo "error: dataset not found at $(DATASET) (expected the crashjs/ dataset checkout)" >&2; \
		exit 1; \
	fi
	ln -sfn $(realpath $(DATASET)) $(LIB)/instrumented

clean:
	rm -rf $(LIB)/node_modules $(LIB)/instrumented $(LIB)/case-staging $(LIB)/package-lock.json

distclean: clean

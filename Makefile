# Top-level convenience targets. The real work lives in predicates/<family>/Makefile
# (oracle builds) and benchmark/ (experiments) — see README.md.

NAME    := drdd-replication
DIST    := dist
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo nogit)

.PHONY: help dist check-clean clean

help:
	@echo "make dist       build $(DIST)/$(NAME)-<version>.tar.gz for distribution"
	@echo "make clean      remove build/packaging leftovers (not oracle libs)"
	@echo ""
	@echo "Oracle libs:    make -C predicates/{crashjs,binutils,ffmpeg}"
	@echo "Reproduction:   python benchmark/scripts/drdd_issre.py"

# Refuse to package a dirty tree. `git archive` reads committed state, so an
# uncommitted change would silently ship the previous snapshot instead - the
# packaging failure mode that is hardest to notice afterwards.
check-clean:
	@git diff-index --quiet HEAD -- || { \
		echo "ERROR: uncommitted changes - git archive would package HEAD, not your tree."; \
		echo "       commit (or stash) first, then re-run 'make dist'."; \
		git status --short; \
		exit 1; \
	}
	@untracked=$$(git ls-files --others --exclude-standard); \
	if [ -n "$$untracked" ]; then \
		echo "ERROR: untracked files would be omitted from the archive:"; \
		echo "$$untracked" | sed 's/^/       /'; \
		echo "       'git add' them (or add to .gitignore), then re-run 'make dist'."; \
		exit 1; \
	fi

# Package exactly the tracked set. This is what makes the distributed tarball
# reproducible: no __pycache__, no *.egg-info, no .venv, no host-built oracle
# libs, and no .git - so what a reviewer unpacks is the artifact, not a
# development directory that happens to contain it.
dist: check-clean
	@mkdir -p $(DIST)
	git archive --format=tar.gz --prefix=$(NAME)/ -o $(DIST)/$(NAME)-$(VERSION).tar.gz HEAD
	@echo ""
	@echo "wrote $(DIST)/$(NAME)-$(VERSION).tar.gz"
	@echo "      $$(tar tzf $(DIST)/$(NAME)-$(VERSION).tar.gz | wc -l) entries, $$(du -h $(DIST)/$(NAME)-$(VERSION).tar.gz | cut -f1)"

clean:
	rm -rf $(DIST)
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
	find src -name '*.egg-info' -type d -prune -exec rm -rf {} +

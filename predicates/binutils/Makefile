# Builds lib/<target>-<tool>-<commit> native host binaries for each configured commit.

REPO   := https://sourceware.org/git/binutils-gdb.git
SRCDIR := build
NPROC  := $(shell nproc)

CFGFLAGS := --disable-shared --disable-gdb --disable-libdecnumber \
            --disable-readline --disable-sim --disable-gprofng \
            --disable-werror --disable-nls

MKFLAGS  := MAKEINFO=true

# Per-commit metadata (add a new commit by declaring FULL_/TGT_/TOOLS_ and appending to COMMITS).
FULL_53f7e8ea  := 53f7e8ea7fad1fcff1b58f4cbd74e192e0bcbc1d
TGT_53f7e8ea   := aarch64-linux
TOOLS_53f7e8ea := readelf

FULL_2870b1ba  := 2870b1ba83fc0e0ee7eadf72d614a7ec4591b169
TGT_2870b1ba   := x86_64-mingw32
TOOLS_2870b1ba := objdump

FULL_a6c21d4a  := a6c21d4a553de184562fd8409a5bcd3f2cc2561a
TGT_a6c21d4a   := x86_64-linux
TOOLS_a6c21d4a := objdump objcopy

FULL_be8e8313  := be8e83130996a5300e15b415ed290de1af910361
TGT_be8e8313   := x86_64-linux
TOOLS_be8e8313 := nm

COMMITS  := 53f7e8ea 2870b1ba a6c21d4a be8e8313

# Build-tree name overrides (binutils suffixes nm/strip with -new during build to
# avoid clobbering host tools; other tools keep their canonical name).
BUILDNAME_nm    := nm-new
BUILDNAME_strip := strip-new

BINARIES := $(foreach c,$(COMMITS),$(foreach t,$(TOOLS_$(c)),lib/$(TGT_$(c))-$(t)-$(c)))

.NOTPARALLEL:
.PHONY: all clean distclean

all: $(BINARIES)

$(SRCDIR):
	git clone $(REPO) $(SRCDIR)

define BUILD_template
$(SRCDIR)/build-$(1)/.built: | $(SRCDIR)
	cd $(SRCDIR) && git checkout -f $(FULL_$(1)) && git clean -fdx -e 'build-*'
	mkdir -p $(SRCDIR)/build-$(1)
	cd $(SRCDIR)/build-$(1) && ../configure --target=$(TGT_$(1)) $(CFGFLAGS)
	$$(MAKE) -C $(SRCDIR)/build-$(1) -j$$(NPROC) $(MKFLAGS) all-binutils
	touch $$@
endef

define COPY_template
lib/$(TGT_$(1))-$(2)-$(1): $(SRCDIR)/build-$(1)/.built
	mkdir -p lib
	cp $(SRCDIR)/build-$(1)/binutils/$(if $(BUILDNAME_$(2)),$(BUILDNAME_$(2)),$(2)) $$@
endef

$(foreach c,$(COMMITS),$(eval $(call BUILD_template,$(c))))
$(foreach c,$(COMMITS),$(foreach t,$(TOOLS_$(c)),$(eval $(call COPY_template,$(c),$(t)))))

clean:
	rm -rf lib/

distclean:
	rm -rf lib/ $(SRCDIR)

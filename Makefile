JASM       = uv run -m jasm
JASMFLAGS  = --nolink
JAIDE      = uv run -m jaide
JAIDEFLAGS = --pit --rtc --graphics --disk  -r

SOURCE_DIR = os
BIN_DIR    = $(SOURCE_DIR)/bin

# used to run the most recently touched binary
LATEST = $(shell ls -t $(BIN_DIR)/*.bin 2>/dev/null | head -1)

.PHONY: nop clean stats test run

# wildcard target considers the build files temporary,
# so we need to make sure they're not deleted
.PRECIOUS: $(BIN_DIR)/%.bin

# assemble any .jasm source in programs/ into a .bin in programs/bin/
# target looks like "programs/bin/program.bin"
# prerequisite looks like "programs/program.jasm"
$(BIN_DIR)/%.bin: $(SOURCE_DIR)/%.jasm
	@mkdir -p $(BIN_DIR)
	@$(JASM) $(JASMFLAGS) $< --output $@

# runs when no target is specified
nop:
	@echo "please specify a program or target:"
	@echo "  make <program name>"
	@echo "  make run"
	@echo "  make test"
	@echo "  make clean"
	@echo "  make stats"
	@true

run:
	@test -n "$(LATEST)" || (echo "no binaries found in $(BIN_DIR)." && exit 1)
	$(JAIDE) $(LATEST) $(JAIDEFLAGS)

test:
	@clear
	@echo "running test suite..."
	@uv run -m pytest -q

disk:
	@echo "creating disk image..."
	@uv run -m jfs create disk.img --add boot.bin --add kernel.bin
	@echo "successfully created disk image."

clean:
	@echo "cleaning up..."
	@rm -rf $(BIN_DIR)
	@echo "successfully cleaned $(BIN_DIR)."

# allow "make program" instead of "make $(SOURCE_DIR)/bin/program.bin"
# last so real rules take priority
# % matches any target, @true just gives the illuson of a non-empty recipe
%: $(BIN_DIR)/%.bin
	@true

JASM       = uv run -m jasm
JASMFLAGS  = --nolink --verbosity 3
JAIDE      = uv run -m jaide
JAIDEFLAGS = --pit --rtc --graphics --disk --verbosity 3 --run
BIN_DIR    = programs/bin

# used to run the most recently touched binary
LATEST = $(shell ls -t $(BIN_DIR)/*.bin 2>/dev/null | head -1)

.PHONY: nop clean test

# wildcard target considers the build files temporary,
# so we need to make sure they're not deleted
.PRECIOUS: $(BIN_DIR)/%.bin

# assemble any .jasm source in programs/ into a .bin in programs/bin/
# target looks like "programs/bin/program.bin"
# prerequisite looks like "programs/program.jasm"
$(BIN_DIR)/%.bin: programs/%.jasm
	@mkdir -p $(BIN_DIR)
	@$(JASM) $(JASMFLAGS) $< --output $@

nop:
	@echo "please specify a program or target:"
	@echo "  make <program name>"
	@echo "  make run"
	@echo "  make test"
	@echo "  make clean"
	@true

run:
	@test -n "$(LATEST)" || (echo "no binaries found in $(BIN_DIR)." && exit 1)
	$(JAIDE) $(LATEST) $(JAIDEFLAGS)

test:
	@clear
	@uv run -m pytest

clean:
	@echo "cleaning up..."
	@rm -rf $(BIN_DIR)
	@echo "successfully cleaned $(BIN_DIR)."

# allow "make program" instead of "make programs/bin/program.bin"
# last so real rules take priority
# % matches any target, @true just gives the illuson of a non-empty recipe
%: $(BIN_DIR)/%.bin
	@true

JASM       = uv run -m jasm
JASMFLAGS  = --nolink
JAIDE      = uv run -m jaide
JAIDEFLAGS = -r -g
BIN_DIR    = programs/bin

# used to run the most recently touched binary
LATEST = $(shell ls -t $(BIN_DIR)/*.bin 2>/dev/null | head -1)

.PHONY: nop clear clean

# wildcard target considers the build files temporary,
# so we need to make sure they're not deleted
.PRECIOUS: $(BIN_DIR)/%.bin

# assemble any .jasm source in programs/ into a .bin in programs/bin/
# target looks like "programs/bin/program.bin"
# prerequisite looks like "programs/program.jasm"
$(BIN_DIR)/%.bin: programs/%.jasm
	@clear
	@mkdir -p $(BIN_DIR)
	@$(JASM) $(JASMFLAGS) $< --output $@
	@$(JAIDE) $(JAIDEFLAGS) $(BIN_DIR)/$<

run:
	@test -n "$(LATEST)" || (echo "no binaries found in $(BIN_DIR)." && exit 1)
	@echo "running $(LATEST)..."
	@$(JAIDE) $(JAIDEFLAGS) $(LATEST)

nop:
	@echo "please specify a program (e.g. make graphics)."
	@true

clean:
	@echo "cleaning up..."
	@rm -rf $(BIN_DIR)
	@echo "successfully cleaned $(BIN_DIR)."


# allow "make program" instead of "make programs/bin/program.bin"
# last so real rules take priority
# % matches any target, @true just gives the illuson of a non-empty recipe
%: $(BIN_DIR)/%.bin
	@true
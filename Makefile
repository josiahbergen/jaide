PYTHON ?= python
BIN_DIR := programs/bin

.PHONY: all assemble run clean FORCE

all: tty.jasm

$(BIN_DIR):
	@mkdir -p $(BIN_DIR)

$(BIN_DIR)/%.bin: programs/%.jasm | $(BIN_DIR)
	@mkdir -p $(dir $@)
	@$(PYTHON) -m jasm $< -o $@

%.jasm: programs/%.jasm $(BIN_DIR)/%.bin FORCE
	@$(PYTHON) -m jaide $(BIN_DIR)/$*.bin

assemble: $(BIN_DIR)/tty.bin

run: tty.jasm

clean:
	@rm -f $(BIN_DIR)/*.bin
	@rm -rf $(BIN_DIR)

FORCE:

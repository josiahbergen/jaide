PYTHON ?= python
BIN_DIR := programs/bin

.PHONY: all assemble run clean

all: tty.jasm

$(BIN_DIR):
	@mkdir -p $(BIN_DIR)

$(BIN_DIR)/%.bin: programs/%.jasm | $(BIN_DIR)
	@$(PYTHON) -m jasm $< -o $@

%.jasm: programs/%.jasm $(BIN_DIR)/%.bin
	@echo "running $<"
	@$(PYTHON) -m jaide $(BIN_DIR)/$*.bin -g -r

assemble: $(BIN_DIR)/tty.bin

run: tty.jasm

clean:
	@rm -f $(BIN_DIR)/*.bin
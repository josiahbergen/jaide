JASM       = uv run -m jasm
JASMFLAGS  = --nolink --nowarn
JAIDE      = uv run -m jaide
JAIDEFLAGS = --pit --rtc --graphics --disk --image jfs/images/disk.img -r

SOURCE_DIR = os
BIN_DIR    = bin

.PHONY: all build run test disk stats clean clear

# wildcard target considers the build files temporary,
# so we need to make sure they're not deleted
.PRECIOUS: $(BIN_DIR)/%.bin

# runs when no target is specified
all: clear build run

build:
	@$(JASM) os/boot.jasm -o bin/boot.bin $(JASMFLAGS)

run:
	@$(JAIDE) bin/boot.bin  $(JAIDEFLAGS)

test:
	@clear
	@echo "running test suite..."
	@uv run -m pytest -q

disk:
	@echo "creating disk image..."
	@uv run -m jfs create disk.img --add boot.bin --add kernel.bin
	@echo "successfully created disk image."

stats:
	@echo
	@cloc --include-ext=jasm,py,md,txt,ebnf --exclude-dir=.venv --read-lang-def=doc/lang/jasm_def.txt .

clean:
	@echo "cleaning up..."
	@rm -rf $(BIN_DIR)
	@echo "successfully cleaned $(BIN_DIR)."

clear:
	@clear

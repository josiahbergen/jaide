JASM       = uv run -m jasm
JASMFLAGS  = --nolink --nowarn
JAIDE      = uv run -m jaide
JAIDEFLAGS = --pit --rtc --graphics --disk --image jfs/images/disk.img -r

SOURCE_DIR = os
BIN_DIR    = bin

ifeq ($(OS),Windows_NT)
CLEAR      = cls
RM_DIR     = if exist $(BIN_DIR) rmdir /s /q $(BIN_DIR)
else
CLEAR      = clear
RM_DIR     = rm -rf $(BIN_DIR)
endif

.PHONY: all build run test disk stats clean clear

all: clear build run

build:
	@$(JASM) os/boot.jasm -o bin/boot.bin $(JASMFLAGS)

run:
	@$(JAIDE) bin/boot.bin $(JAIDEFLAGS)

test: clear
	@echo running test suite...
	@uv run -m pytest -q

disk:
	@echo creating disk image...
	@uv run -m jfs create disk.img --add boot.bin --add kernel.bin
	@echo "successfully created disk image."

stats: clear
	@cloc --include-ext=jasm,py,md,txt,ebnf --exclude-dir=.venv --read-lang-def=doc/lang/jasm_def.txt .

clean:
	@echo cleaning up...
	@$(RM_DIR)
	@echo "successfully cleaned $(BIN_DIR)."

clear:
	@$(CLEAR)

JASM       = uv run -m jasm -v 0
JASMFLAGS  = --nolink --nowarn
EMULATOR      = uv run -m emulator
EMULATORFLAGS = --pit --rtc --graphics --disk --image jfs/images/disk.img -r

SOURCE_DIR = kernel
BIN_DIR    = bin

ifeq ($(OS),Windows_NT)
CLEAR      = cls
RM_DIR     = if exist $(BIN_DIR) rmdir /s /q $(BIN_DIR)
else
CLEAR      = clear
RM_DIR     = rm -rf $(BIN_DIR)
endif

.PHONY: all build run disk stats clean clear help

all: clear build run

build:
	@$(JASM) $(SOURCE_DIR)/boot.jasm -o bin/boot.bin $(JASMFLAGS)

run:
	@$(EMULATOR) bin/boot.bin $(EMULATORFLAGS)

# test: clear
# 	@echo running test suite...
# 	@uv run -m pytest

disk:
	@echo creating disk image...
	@uv run -m jfs create disk.img --add boot.bin --add kernel.bin
	@echo "successfully created disk image."

stats: clear
	@cloc --include-ext=jasm,py,md,txt,ebnf --exclude-dir=.venv --read-lang-def=docs/lang/jasm_def.txt .

clean:
	@echo cleaning up...
	@$(RM_DIR)
	@echo "successfully cleaned $(BIN_DIR)."

clear:
	@$(CLEAR)

help:
# 	@echo "--------------------------------"
	@echo "usage: make <target>"
	@echo "targets:"
	@echo "  (none)  build all and run"
	@echo "  build   build only"
	@echo "  run     run only"
	@echo "  test    run test suite"
	@echo "  stats   show statistics"
	@echo "  clean   clean build directory"
	@echo "  help    show this message"
# 	@echo "--------------------------------"

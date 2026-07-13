# known problems

- `BCP` bypasses the memory bus, including ROM protection, MMIO, banking boundaries, and address wrapping.
- shift flag behavior and out-of-range shift counts are not fully defined or handled.
- `SBC` treats carry as borrow even though `SUB` sets carry when no borrow occurred.
- opcodes are assigned from dictionary order, so adding or moving an instruction variant can renumber the ISA.
- assembler options are dropped by `generate_context`; the `--nolink` check also appears inverted.
- assembler imports resolve relative to the working directory, and label namespaces collide for files with the same basename.
- assembler library errors call `sys.exit()` instead of raising structured exceptions.
- `load_binary` treats its address as a byte offset even though jaide uses word addresses; it also bypasses memory mapping.
- interrupt instructions, interrupt handling, and the interrupt-enable flag are documented/parsed but not implemented.
- syscall IDs and MMIO definitions are duplicated across Python, JASM, and documentation and have drifted.
- graphics control uses `0x40` instead of an address in the `0xFE00–0xFEFF` MMIO range.
- JFS uses native-endian `array("H")`, disagrees with the docs about byte/word file sizes, cannot represent empty files, and does not handle an out-of-space disk cleanly.
- packaging is not configured; `uv build` fails because multiple top-level packages are auto-discovered.
- test and lint tools are runtime dependencies, and Ruff currently checks only import ordering.
- logger implementations are duplicated and global; emulator/library code exits the whole process in several places.
- the REPL runs inside its constructor and bypasses mapped memory for some debugger commands.
- the Makefile Windows check references `$(jaideos)` instead of `$(OS)`, and the `disk` target uses unsupported JFS arguments.
- device, filesystem, reset, assembler-option, and CLI/build paths need more integration coverage.

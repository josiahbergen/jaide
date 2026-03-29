# Jaide: Tech Demo to OS-Ready Hardware -- Roadmap

## Context

Jaide is a 16-bit custom computing architecture with a working emulator, assembler, and graphics subsystem. It can run simple programs (blink demos, fibonacci). The goal is to close every gap in the ISA, assembler, emulator, and spec that would prevent writing an operating system capable of running a shell, text editor, and loading/executing user binaries. This plan does NOT cover building the OS itself -- only preparing the platform.

The user's three stated priorities: **position-independent code**, **software interrupts / syscalls**, and **proper device interfaces** (disk, GPU, keyboard, timer).

---

## Bugs and Spec Errors Found During Audit

These must be understood before any work begins:

### B1. LSH/RSH flag computation untested
Both `_lsh_core` and `_rsh_core` in `emulator.py` have `# TODO: test` comments. The overflow flag computation reuses the addition pattern `(a ^ b) & 0x80`, which is wrong for shifts.
- **File**: `jaide/emulator.py:328-344`

---

## Phase 0: Foundation (Safety Net + Critical Fixes)

**Goal**: Fix the most dangerous bugs and establish a test harness before changing anything else.

### 0.1 -- Create test infrastructure
- Add `tests/` directory with pytest
- `tests/test_alu.py` -- unit tests for `_add_core`, `_sub_core`, `_lsh_core`, `_rsh_core` with known inputs/outputs and flag verification
- `tests/test_instructions.py` -- integration tests: assemble small snippets, load into emulator, step through, verify register/memory/flag state
- `tests/test_assembler.py` -- assemble known `.jasm` snippets, compare byte output
- `tests/conftest.py` -- shared fixtures (fresh Emulator, assemble-and-load helper)
- **Files**: `tests/` (new), `pyproject.toml` (add pytest dep)

### 0.2 -- Fix CMP operand order
- In `handle_cmp`: swap to `_sub_core(reg_b, reg_a)` for reg-reg, `_sub_core(reg_a, imm16)` for reg-imm
- Update `doc/inst.txt` CMP pseudocode to `flags <- dest - src`
- Write CMP-specific tests that lock in the corrected semantics
- **Files**: `jaide/emulator.py`, `doc/inst.txt`

### 0.3 -- Fix LSH/RSH flags
- `_lsh_core`: carry = last bit shifted out = `(a >> (16 - b)) & 1` when `0 < b <= 16`. Overflow = MSB changed.
- `_rsh_core`: carry = `(a >> (b - 1)) & 1` when `b > 0`. Overflow = 0.
- Handle shift amounts of 0 and >= 16 as edge cases.
- Write tests for all edge cases.
- **Files**: `jaide/emulator.py:328-344`

### 0.4 -- Fix exception handling (div-by-zero, invalid opcode)
- `handle_mod`: replace `raise EmulatorException` with `self.request_interrupt(0); return`
- `decode()`: on unknown opcode, fire `request_interrupt(1)` instead of `self.halted = True`
- **Files**: `jaide/emulator.py`

### 0.5 -- Fix documentation errors
- `CLAUDE.md`: fix banking range to `0x0200-0x41FF`
- `doc/graphics.md`: fix resolution to "80x25 8x16 glyphs"
- `doc/inst.txt`: add missing MOV/CALL modes
- **Files**: `CLAUDE.md`, `doc/graphics.md`, `doc/inst.txt`

---

## Phase 1: ISA Completions

**Goal**: Fill the instruction set gaps that would block OS-level code.

Each item touches `common/isa.py` (add to INSTRUCTIONS enum, INSTRUCTION_MODES, _FORMAT_DATA), `jaide/emulator.py` (add handler), and `jasm/language/grammar.py` (add mnemonic to regex if needed). Tests for each.

### 1.1 -- Add DIV instruction
- `DIV reg, reg` and `DIV reg, imm16`: unsigned integer division, `dest <- dest / src`
- Sets Z (result zero), C (remainder nonzero), N, O flags
- Division by zero fires interrupt vector 0 (same as MOD fix in 0.4)
- Pattern follows MUL/MOD exactly

### 1.2 -- Add ASR (Arithmetic Shift Right)
- `ASR reg, reg` and `ASR reg, imm16`: right shift preserving sign bit
- Essential for signed arithmetic (signed division by powers of 2)
- Handler: sign-extend to Python int, shift, mask back to 16-bit
- Carry = last bit shifted out. Zero flag. No overflow.

### 1.3 -- Add PUT with REL_POINTER mode
- `PUT [label], reg` -- store to a PC-relative address
- **This is the single most important change for position-independent code.** GET already has `[pc + simm]` but PUT doesn't, meaning PIC code cannot write to global/static data without a multi-instruction address-load workaround.
- Add `(MODES.REL_POINTER, MODES.REG)` to `INSTRUCTION_MODES[PUT]`
- Add format entry: `(1, None, 0)` -- src register in ssss, immediate is PC-relative offset
- Add handler branch in `handle_put`

### 1.4 -- Add XCHG (Exchange Registers) [optional, low priority]
- `XCHG reg, reg`: swap two registers atomically
- Saves 3 instructions (push/mov/pop pattern) during context switches
- Not strictly required; defer if timeline is tight

---

## Phase 2: Assembler Modernization

**Goal**: Make the assembler capable of producing the code an OS developer needs.

### 2.1 -- ORG directive
- `ORG 0x0200` sets the origin/load address for label resolution
- `AssemblyContext.origin` already exists (defaults to 0) but has no syntax to set it
- Add grammar rule, IR node (`OrgDirectiveNode`), transformer handler
- In `labels.py`: when encountered, set `pc` to the specified value
- **Files**: `jasm/language/grammar.py`, `jasm/language/ir/base.py`, `jasm/language/transformer.py`, `jasm/labels.py`

### 2.2 -- EQU / DEFINE for named constants
- `SCREEN_WIDTH EQU 80` or `DEFINE SCREEN_WIDTH 80`
- Store in `context.constants` (separate from labels to avoid PC-relative encoding)
- During label resolution, when a `LabelOperand` name matches a constant, replace with `ImmediateOperand`
- **Files**: `jasm/language/grammar.py`, `jasm/language/ir/base.py`, `jasm/language/transformer.py`, `jasm/language/context.py`, `jasm/labels.py`

### 2.3 -- Expression evaluation
- `ExpressionOperand` already parsed by grammar but throws `logger.fatal("not yet implemented")`
- Implement recursive evaluator for `+`, `-`, `*`, `/`, `%`, `<<`, `>>`, `&`, `|`, `^`, `~`
- Operates on numeric literals and EQU constants
- Returns `ImmediateOperand` with computed value
- **Files**: `jasm/language/transformer.py`, `jasm/language/ir/operands.py`

### 2.4 -- RESW / RESB / TIMES directives
- `RESW 256` -- reserve 256 zero-filled words (for BSS, buffers, IVT init)
- `TIMES 512, 0xFF` -- fill 512 words with a value
- New IR node type, encodes to bytearray in `binary.py`
- **Files**: `jasm/language/grammar.py`, `jasm/language/ir/base.py`, `jasm/language/transformer.py`, `jasm/binary.py`

### 2.5 -- String escape sequences
- Currently `DataDirectiveNode.parse_string` does raw `ord(char)` -- no `\n`, `\0`, `\t`, `\\`
- Add `unescape()` function processing C-style escapes before character conversion
- **File**: `jasm/language/ir/base.py`

### 2.6 -- ALIGN directive
- `ALIGN 16` pads with zeros until PC is aligned to boundary
- In `labels.py`: compute `padding = (alignment - (pc % alignment)) % alignment`, advance PC
- In `binary.py`: emit zero words for padding
- **Files**: `jasm/language/grammar.py`, `jasm/language/ir/base.py`, `jasm/language/transformer.py`, `jasm/labels.py`, `jasm/binary.py`

---

## Phase 3: Device Layer

**Goal**: Give the emulated CPU enough peripherals to run an OS.

### 3.0 -- Device abstraction layer
Create a base `Device` class and `DeviceManager` so the emulator manages all devices uniformly:
```python
class Device:
    def port_read(self, port: int) -> int: ...
    def port_write(self, port: int, value: int): ...
    def tick(self): ...  # called once per CPU cycle
```
Refactor `port_get`/`port_set` to dispatch to owning device. Add `tick()` call in the `step()` loop.
- **Files**: `jaide/devices/__init__.py` (new base class), `jaide/emulator.py` (refactor port dispatch, add tick loop)

### 3.1 -- Programmable Interval Timer (PIT) [CRITICAL for OS]
Without a timer, there is no preemptive multitasking, no `sleep()`, no time-slicing.
- **Ports**: 0x10 (control: enable/mode bits), 0x11 (reload value in cycles), 0x12 (current count, read-only)
- **Interrupt**: Vector 5
- **Behavior**: Each `tick()` decrements counter. At zero: fire interrupt, reload if periodic mode.
- **File**: `jaide/devices/timer.py` (new)

### 3.2 -- Disk Controller [CRITICAL for OS]
Without disk I/O, the OS can't load programs or persist data. The user already has a JFS filesystem spec in `doc/file.md`.
- **Ports**: 0x20 (command: READ_SECTOR/WRITE_SECTOR/STATUS), 0x21 (sector number), 0x22 (memory address hi), 0x23 (memory address lo), 0x24 (status: busy/error/done bits)
- **Interrupt**: Vector 6 on transfer complete
- **Backend**: Host filesystem binary file (`--disk disk.img` CLI arg)
- **DMA-style transfer**: On READ command, copy 256 words into emulator memory over 256 ticks (one word per tick), then fire completion interrupt. Avoids word-by-word programmed I/O.
- **File**: `jaide/devices/disk.py` (new), `jaide/__main__.py` (add `--disk` arg)

### 3.3 -- Keyboard device refactor
Currently hardcoded in `emulator.py:282-289` with direct queue polling and magic constants. Move to a `KeyboardDevice` subclass.
- Port 1, interrupt vector 4 become device constants
- `key_queue` passed to device instead of emulator
- **Files**: `jaide/devices/keyboard.py` (new), `jaide/emulator.py` (remove hardcoded logic)

### 3.4 -- Real-Time Clock (RTC)
Simple read-only device providing wall-clock time through ports.
- **Ports**: 0x30 (seconds), 0x31 (minutes), 0x32 (hours), 0x33 (day-of-year)
- No interrupt; software polls when needed.
- **File**: `jaide/devices/rtc.py` (new)

### 3.5 -- Console device (upgrade port 0)
Port 0 currently does `print(chr(value))` inline. Wrap in a proper `ConsoleDevice` with status port (0x02: output ready, input available bits). Enables headless/debug operation alongside the graphics display.
- **File**: `jaide/devices/console.py` (new)

---

## Phase 4: Conventions, Spec, and ABI

**Goal**: Document everything an OS programmer needs to know without reading emulator source.

### 4.1 -- Calling convention / ABI (`doc/abi.md`, new)
- Arguments: first 4 in A, B, C, D; extras on stack right-to-left
- Return value: A
- Caller-saved: A, B, C, D, E (volatile)
- Callee-saved: X, Y, Z, SP, MB (non-volatile)
- Stack frame: no mandatory frame pointer; Z optionally used as FP
- SP must be word-aligned at all times

### 4.2 -- Syscall convention (`doc/syscalls.md`, new)
- Syscalls use `INT 0x80` (vector 128) -- or pick a vector in the 16-47 range
- Syscall number in A, arguments in B, C, D, E
- Return value in A
- OS installs handler at corresponding IVT entry
- Define initial syscall numbers: read, write, open, close, exec, exit, sbrk

### 4.3 -- Formalize interrupt vector allocation (update `doc/spec.md`)

| Vector | Type | Purpose |
|--------|------|---------|
| 0 | Exception | Division by zero / general fault |
| 1 | Exception | Invalid opcode |
| 2 | Exception | Protection fault (future) |
| 3 | Reserved | Reserved |
| 4 | Hardware | Keyboard |
| 5 | Hardware | Timer (PIT) |
| 6 | Hardware | Disk controller |
| 7-15 | Hardware | Reserved for future devices |
| 16-47 | Software | OS syscalls |
| 48-255 | Software | User-defined |

### 4.4 -- Formalize port allocation (update `doc/spec.md`)

| Port Range | Device |
|-----------|--------|
| 0x00-0x02 | Console (serial) |
| 0x10-0x12 | Timer (PIT) |
| 0x20-0x24 | Disk controller |
| 0x30-0x33 | RTC |
| 0x40-0x4F | Reserved (GPU control) |
| 0xFF | System control |

### 4.5 -- Boot sequence document (`doc/boot.md`, new)
1. CPU starts at PC=0x0000 (ROM)
2. ROM bootloader initializes SP to 0xFEFF
3. Bootloader reads sector 0 from disk into memory at a defined address (e.g., 0x0200 or 0x4200)
4. Bootloader jumps to loaded code
5. Kernel sets up IVT, initializes devices, enables interrupts

### 4.6 -- Fix graphics.md and consolidate VRAM spec
- Correct resolution discrepancy (80x25 / 8x16, not 80x50 / 8x8)
- Ensure VRAM word structure, color palette, and bank assignment are fully documented

---

## Phase 5: Tooling and Developer Experience

**Goal**: Make it practical to develop and debug OS-level code.

### 5.1 -- Improved REPL disassembler
Current `disasm_at` shows raw register indices. Upgrade to:
- Show register names in context (`MOV A, 0x0200` not `MOV 0 1 0200`)
- Resolve PC-relative targets to absolute addresses
- Range disassembly: `disasm 0x0000 0x0020`
- Show hex bytes alongside mnemonics
- **File**: `jaide/repl.py`

### 5.2 -- Symbol file output from assembler
- Add `-s` / `--symbols` flag that writes a `.sym` file (label name -> word address)
- REPL `loadsym` command loads symbol file, shows labels in disassembly
- **Files**: `jasm/__main__.py`, `jasm/jasm.py`, `jaide/repl.py`

### 5.3 -- Memory watchpoints
- `watch 0xFE00` breaks when any instruction writes to that address
- Essential for debugging memory corruption
- **Files**: `jaide/repl.py`, `jaide/emulator.py` (check in `write16`)

### 5.4 -- Instruction counter / cycle profiling
- Track instruction count, per-opcode frequency
- `profile` REPL command shows stats
- **Files**: `jaide/emulator.py`, `jaide/repl.py`

### 5.5 -- Disk image creation tool
- Python utility to create JFS-formatted disk images per `doc/file.md` spec
- `python -m jfs create disk.img --add boot.bin --add kernel.bin`
- **Files**: `jfs/` (new package)

### 5.6 -- Linker (stretch goal, builds on existing `doc/plan.md` design)
The existing `doc/plan.md` already designs a `.jo` object format and `jlink` linker. Implementation:
- Add `EXPORT` / `EXTERN` directives to assembler grammar
- Add `-c` (compile-only) flag to emit `.jo` relocatable objects instead of flat binary
- Build `jlink` package that reads `.jo` files, resolves symbols, patches relocations, emits final binary
- Not strictly required for a first OS (single-file assembly with IMPORT works), but needed for multi-module builds
- **Files**: `jlink/` (new), `jasm/language/grammar.py`, `jasm/binary.py`

---

## Execution Order and Dependencies

```
Phase 0 (Foundation) ──────────────────────────────────────
  0.1 Test infrastructure
  0.2 Fix CMP ←─ needs tests from 0.1
  0.3 Fix LSH/RSH flags
  0.4 Fix exception interrupts (div-by-zero, invalid opcode)
  0.5 Fix documentation
         │
Phase 1 (ISA) ─────────────────────────────────────────────
  1.1 DIV ──────────┐
  1.2 ASR ──────────┤ all independent, can parallelize
  1.3 PUT [label] ──┘
         │
    ┌────┴────┐
Phase 2       Phase 3
(Assembler)   (Devices)         ← can develop in parallel
  2.1 ORG       3.0 Device abstraction
  2.2 EQU       3.1 Timer (PIT)
  2.3 Exprs     3.2 Disk controller
  2.4 RESW      3.3 Keyboard refactor
  2.5 Escapes   3.4 RTC
  2.6 ALIGN     3.5 Console device
    └────┬────┘
         │
Phase 4 (Conventions & Spec) ──────────────────────────────
  4.1-4.6 Documentation (can be written as features land)
         │
Phase 5 (Tooling) ─────────────────────────────────────────
  5.1 Disassembler
  5.2 Symbol files
  5.3 Watchpoints
  5.4 Profiling
  5.5 Disk image tool ←─ depends on 3.2
  5.6 Linker (stretch)
```

---

## What is intentionally NOT in this roadmap

- **Privilege levels / supervisor mode / MMU**: Important for a production OS but not required for a first OS on an emulated single-user system. The OS author can enforce discipline without hardware protection. Add in a future "Phase 6: Hardening" after the first OS boots.
- **Virtual memory / paging**: Not feasible without radical architecture changes. Defer indefinitely.
- **Mouse / audio / networking**: Not needed for shell + text editor.
- **High-level language / compiler**: Far future. The assembler must be solid first.
- **The OS itself**: Out of scope per user request.

---

## Verification Plan

After each phase, verify with an end-to-end smoke test:

- **Phase 0**: Run existing `programs/blink.jasm` -- should still work. Run new test suite -- all pass.
- **Phase 1**: Write a small PIC test program using `PUT [label], reg`, `DIV`, `ASR`. Assemble, load at a non-zero origin, verify correct execution.
- **Phase 2**: Write a program using `ORG 0x0200`, `EQU`, `RESW`, `ALIGN`, expressions. Assemble and verify binary output.
- **Phase 3**: Write a program that sets up a timer interrupt handler, reads a sector from disk, and echoes keyboard input. Run with `--disk` and `-g` flags.
- **Phase 4**: N/A (documentation review).
- **Phase 5**: Assemble with `--symbols`, load symbols in REPL, disassemble with labels showing, set a watchpoint, verify it fires.

---

## Critical Files Summary

| File | Touched In |
|------|-----------|
| `common/isa.py` | Phase 0 (CMP fix), Phase 1 (all ISA additions) |
| `jaide/emulator.py` | Phase 0, 1, 3 (handlers, exceptions, device integration) |
| `jasm/language/grammar.py` | Phase 1 (new mnemonics), Phase 2 (all directives) |
| `jasm/language/ir/base.py` | Phase 2 (new IR node types) |
| `jasm/language/transformer.py` | Phase 2 (directive handlers, expression eval) |
| `jasm/labels.py` | Phase 2 (ORG, ALIGN, EQU resolution) |
| `jasm/binary.py` | Phase 2 (RESW/ALIGN encoding) |
| `jaide/devices/` | Phase 3 (all new device modules) |
| `jaide/repl.py` | Phase 5 (disassembler, watchpoints, profiling) |
| `doc/spec.md` | Phase 0, 4 (all spec updates) |
| `doc/inst.txt` | Phase 0, 1 (instruction reference updates) |

# Jaide: Revised Roadmap (April 2026)

## Context

Jaide is a 16-bit custom computing architecture with a working emulator, assembler, graphics
subsystem, filesystem tooling, and a partial kernel. The platform goal is a DOS-like operating
system: a command-line shell from which you can navigate, run programs, and manage files. The
flagship demo applications are a **word processor** (render and save markdown-like text files) and
an **assembly editor** (write machine code, assemble in-memory, load and execute it).

A second hard constraint is **physical buildability**. Every architectural decision should remain
within reach of discrete logic ICs, a small FPGA, or off-the-shelf microcontrollers. No MMU,
no privilege levels, no virtual memory.

---

## What is already done

The following items from the previous roadmap are complete and do not need revisiting.

| Item                     | Notes                                                                                                             |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| Device abstraction layer | `jaide/devices/device.py` — base `Device` class with port dispatch and `tick()`                                   |
| PIT timer                | `jaide/devices/pit.py` — ports 0x10/0x11, interrupt vector 5                                                      |
| Keyboard device          | `jaide/devices/keyboard.py` — port 0x01/0x02, interrupt vector 4                                                  |
| RTC device               | `jaide/devices/rtc.py` — ports 0x30-0x33, read-only                                                               |
| JFS disk image tool      | `jfs/` package — `create`, `info`, `read` subcommands working                                                     |
| Bootloader               | `os/boot.jasm` — sets IVT entries for vectors 0-4, sets SP, aligns to 0x200                                       |
| Kernel shell             | `os/kernel.jasm` — keyboard input, command buffer, `dispatch_command`, stubs for `help`/`list`/`mount`/`shutdown` |
| Graphics macros          | `os/graphics.jasm` — `string_at`, `blink_at`, `xy_to_vram`, `print`                                               |
| String utilities         | `os/util.jasm` — `string_compare`, `serial_out`, `dereference_into`, `put_value_at`                               |

---

## Phase A: Disk Controller (hard blocker)

**Goal**: Give the emulator a working disk device so the kernel can load files and executables.

The JFS filesystem format is already specced and the image creation tool is done. This phase
wires the emulator to a `.img` file via a port-mapped disk controller, matching what a physical
SPI SD-card controller would expose.

### A.1 — Disk controller device (`jaide/devices/disk.py`)

The disk controller exposes five ports and fires interrupt vector 6 on transfer completion.

**Ports:**

| Port | Direction | Purpose                                              |
| ---- | --------- | ---------------------------------------------------- |
| 0x20 | W         | Command: `0x01` = READ_SECTOR, `0x02` = WRITE_SECTOR |
| 0x21 | W         | Sector number (0-indexed)                            |
| 0x22 | W         | Destination/source memory address (high byte)        |
| 0x23 | W         | Destination/source memory address (low byte)         |
| 0x24 | R         | Status: bit 0 = busy, bit 1 = done, bit 2 = error    |

**Transfer behavior:**

When a READ or WRITE command is issued (write to port 0x20), the controller enters BUSY state and
begins transferring one word per `tick()` call. After `BLOCK_SIZE` (256) words, it clears BUSY,
sets DONE, and fires interrupt vector 6. This pacing mirrors real SPI SD-card behavior and avoids
instantaneous memory copies that would be impossible to replicate in hardware.

The address written to ports 0x22/0x23 is split hi/lo so that it fits within 8-bit port writes.
The kernel assembles the full 16-bit address before issuing the command.

**Backend**: reads/writes to the host `.img` file opened at startup. Sector size = 256 words =
512 bytes (matching JFS `BLOCK_SIZE`).

- **File**: `jaide/devices/disk.py`

### A.2 — Wire disk device into the emulator (`jaide/emulator.py`, `jaide/__main__.py`)

- Add `--disk <path>` CLI flag.
- When `--disk` is provided, instantiate `DiskController(path, self.raise_interrupt)` and append
  to `self.devices`.
- The device's `tick()` is already called in the main `step()` loop via the device list.
- Log which devices are active at startup.

- **Files**: `jaide/__main__.py`, `jaide/emulator.py`

### A.3 — Kernel disk interface (`os/kernel.jasm`, `os/util.jasm`)

Add assembly-language wrappers for the disk controller so the rest of the kernel can call a
clean subroutine instead of manually poking ports.

```txt
; disk_read_sector
; read one sector from disk into memory.
;   sector = sector index (immediate or register)
;   dest   = destination word address
; fires interrupt on completion; caller should halt and wait.
```

Wire up the disk interrupt handler in the bootloader IVT (vector 6 → `kernel__disk_interrupt`).
The simplest strategy for now: disk operations are synchronous from the kernel's point of view —
issue the command, loop on HALT until the disk interrupt sets a flag, then proceed.

- **Files**: `os/boot.jasm` (IVT entry for vector 6), `os/util.jasm` (disk subroutines)

### A.4 — Implement `mount` and `list` commands

Once the disk device exists, replace the hardcoded error strings in `kernel.jasm`:

- `mount`: read block 0 (the JFS boot block) from sector 0, validate the magic number
  (`0x333A`), store the filesystem header fields in kernel variables.
- `list`: walk the root directory table (location stored from `mount`), print each entry's
  filename and extension to the screen.

This is the first real end-to-end disk I/O test.

---

## Phase B: EXEC and the User Program ABI

**Goal**: Load a binary from disk and run it. Return to the shell when it exits.

### B.1 — Executable format and memory map

User programs are flat binaries assembled to load at address `0x4000`. This is above the kernel
(which lives at `0x0200–~0x3FFF`) and below the stack (`0xFE00`).

```txt
0x0000 - 0x01FF   ROM (bootloader, 512 words)
0x0200 - 0x3FFF   Kernel (~15.5 KiB)
0x4000 - 0xFDFF   User program space (~47 KiB)
0xFE00 - 0xFEFF   Stack (256 words, grows down)
0xFF00 - 0xFFFF   IVT (256 vectors)
```

User programs:

- Are assembled with `org 0x4000`.
- Have their entry point at the first word of the binary (address 0x4000).
- Use `INT 0x10` to make kernel syscalls.
- Signal exit by returning from the entry point (RET) or calling `INT 0x10` with syscall `exit`.

The kernel's `exec` implementation: look up the filename in the root directory, compute the
sector list from the FAT, read all sectors into memory starting at 0x4000, then `CALL 0x4000`.
When that call returns, control is back in the shell.

- **Files**: `os/kernel.jasm` (exec logic), document in `doc/abi.md`

### B.2 — Syscall interface

User programs need kernel services without hardcoding kernel addresses. The convention:

- **Instruction**: `INT 0x10` (vector 16)
- **Syscall number**: register A
- **Arguments**: B, C, D, E
- **Return value**: A (0 = success unless noted). Multi-value returns use B/C as additional output
  registers where documented.
- Caller-saved registers: A, B, C, D, E. Callee-saved: X, Y, Z, SP, MB.

The bootloader (`boot.jasm`) must install a handler for vector 16 that dispatches to the kernel's
syscall router. The kernel's syscall router is a jump table indexed by A.

#### Syscall table

##### Group 0x00 — Process

| #      | Name   | Args              | Returns                              | Notes                                                      |
| ------ | ------ | ----------------- | ------------------------------------ | ---------------------------------------------------------- |
| `0x00` | `exit` | B = exit code     | —                                    | Return to shell. No-op if called from shell context.       |
| `0x01` | `exec` | B = filename addr | A = error (never returns on success) | Look up file in root dir, load to `0x4000`, `CALL 0x4000`. |

`exit` is the only graceful way a user program terminates from deep in its call stack. A plain
`RET` from address `0x4000` also works and returns to the shell naturally.

##### Group 0x10 — Terminal output

| #      | Name           | Args                   | Returns      | Notes                                                                                                                      |
| ------ | -------------- | ---------------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------- |
| `0x10` | `write_string` | B = addr               | —            | Print null-terminated string at cursor. Scrolls.                                                                           |
| `0x11` | `write_char`   | B = char               | —            | Print one character. Advances cursor. Scrolls at EOL.                                                                      |
| `0x12` | `clear_screen` | —                      | —            | Blank VRAM, reset cursor to (0, 0).                                                                                        |
| `0x13` | `set_cursor`   | B = x, C = y           | —            | Move kernel cursor. x: 0–79, y: 0–24.                                                                                      |
| `0x14` | `get_cursor`   | —                      | B = x, C = y | Read current cursor position.                                                                                              |
| `0x15` | `put_char_at`  | B = char, C = x, D = y | —            | Write one glyph directly to VRAM. No cursor update, no scroll.                                                             |
| `0x16` | `set_color`    | B = attr               | —            | Set color attribute for subsequent `write_*` calls. Low nibble = fg, next nibble = bg. Default: `0x0001` (white on black). |

`write_string`/`write_char` are for the shell's streaming output model. `put_char_at` is the
primitive full-screen apps (word processor, assembly editor) use to redraw arbitrary cells
without triggering scroll or cursor movement.

##### Group 0x20 — Terminal input

| #      | Name        | Args                      | Returns       | Notes                                                                                                         |
| ------ | ----------- | ------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------- |
| `0x20` | `read_char` | —                         | A = char      | **Blocking.** STI + HALT until a key arrives. Returns raw key code including special keys (arrows, Ctrl+key). |
| `0x21` | `poll_key`  | —                         | A = char or 0 | **Non-blocking.** Returns next key from buffer, or 0 if empty.                                                |
| `0x22` | `read_line` | B = buf addr, C = max len | A = length    | Collect input with echo and backspace until Enter; null-terminate buffer.                                     |

`read_char` returns the raw 16-bit key code unfiltered. The shell uses `read_line`; full-screen
apps use `read_char` in a tight event loop.

##### Group 0x30 — Filesystem

| #      | Name       | Args                                | Returns                                        | Notes                                                                                                                                                 |
| ------ | ---------- | ----------------------------------- | ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `0x30` | `fs_mount` | —                                   | A = status                                     | Read boot sector, validate magic (`0x333A`), cache FS header in kernel vars. Must succeed before other `fs_*` calls. Replaces current syscall `0x00`. |
| `0x31` | `fs_list`  | B = entry buf addr, C = max entries | A = count                                      | Copy root directory entries into caller-provided buffer. Each entry is 8 words (matches JFS layout).                                                  |
| `0x32` | `fs_open`  | B = filename addr                   | A = fd                                         | Walk root dir, return index into kernel FD table. Error if not found.                                                                                 |
| `0x33` | `fs_read`  | B = fd, C = dest addr, D = n_words  | A = words read                                 | Read words from current file position, following FAT chain.                                                                                           |
| `0x34` | `fs_write` | B = fd, C = src addr, D = n_words   | A = status                                     | Write words at current file position. Allocates new blocks as needed.                                                                                 |
| `0x35` | `fs_seek`  | B = fd, C = word offset             | A = status                                     | Move read/write position within file.                                                                                                                 |
| `0x36` | `fs_close` | B = fd                              | —                                              | Release FD table slot. Flush any pending writes.                                                                                                      |
| `0x37` | `fs_stat`  | B = filename addr                   | A = status, B = start block, C = size in words | Query file metadata without opening.                                                                                                                  |

The kernel maintains a small FD table (~4 slots) in kernel RAM. Each slot stores: start block,
current block, word offset within block, and total size in words.

##### Group 0x40 — System

| #      | Name        | Args | Returns                                              | Notes                                                          |
| ------ | ----------- | ---- | ---------------------------------------------------- | -------------------------------------------------------------- |
| `0x40` | `get_ticks` | —    | A = low word, B = high word                          | 32-bit kernel tick counter, incremented by PIT ISR (vector 5). |
| `0x41` | `get_time`  | —    | A = year, B = month, C = day, D = hours, E = minutes | Read RTC (ports `0x30–0x33`).                                  |
| `0x42` | `shutdown`  | —    | —                                                    | `OUTB 0xFF, 0x03`.                                             |
| `0x43` | `reset`     | —    | —                                                    | `OUTB 0xFF, 0x01`.                                             |

#### Migration from existing stubs

| Current                          | Replacement                                        |
| -------------------------------- | -------------------------------------------------- |
| `syscall 0x00` (mount)           | `fs_mount` (`0x30`) — same behavior, new number    |
| `syscall 0x01` (disk_info stub)  | `fs_stat` (`0x37`)                                 |
| `handler_exit` direct OUTB       | `shutdown` (`0x42`)                                |
| `echo`/`print`/`scroll` in shell | `write_string` (`0x10`) kernel-side implementation |
| `clear_screen` in shell          | `clear_screen` (`0x12`) kernel-side implementation |

The shell will call through the syscall layer for all output so the word processor and shell
share one implementation.

- **Files**: `os/boot.jasm` (IVT entry 16), `os/kernel.jasm` (syscall dispatch table and
  handlers), `doc/syscalls.md` (new)

### B.3 — `exec` shell command

Wire a new `exec` command (or use a bare filename as the default shell behavior) that calls the
kernel's exec routine. Minimal version:

```txt
exec <filename>
```

Looks up `<filename>` in the root directory, loads it to 0x4000, calls it, returns to shell when
done.

---

## Phase C: Shell Quality of Life

**Goal**: Make the shell usable as a real interactive environment.

### C.1 — Display scrolling

Currently, command output is always written to row 2 and subsequent commands overwrite it. The
shell needs a scrolling output region (rows 2–24) so output accumulates naturally.

Implementation:

- Maintain a cursor tracking the next output row.
- When the cursor reaches row 24, shift VRAM rows 2–24 up by one row (copy 160 words at a time),
  clear row 24, write output there.
- The VRAM shift is done by the kernel; user programs call the `write_string` syscall and the
  kernel handles scrolling transparently.

- **File**: `os/kernel.jasm` (scroll routine, cursor tracking)

### C.2 — Cursor and input line management

Currently the input line is hardcoded to row 1. After scrolling is implemented, the input line
should stay fixed at the bottom (row 24) while output scrolls in the region above.

Alternative (simpler, more DOS-like): the prompt is always at the bottom of the output stream.
After each command, print a new prompt on the next available line. This is easier to implement
and feels more natural.

- **File**: `os/kernel.jasm`

### C.3 — Additional built-in commands

Once disk I/O and exec work:

| Command       | Behavior                                     |
| ------------- | -------------------------------------------- |
| `help`        | List available commands                      |
| `list`        | List files on disk (already planned in A.4)  |
| `exec <file>` | Load and run a program from disk             |
| `shutdown`    | Halt via system port (already exists)        |
| `clear`       | Fill output region with spaces, reset cursor |

---

## Phase D: Assembler Expression Evaluation

**Goal**: Remove the last `logger.fatal("not yet implemented")` in the assembler.

### D.1 — Expression evaluator (`jasm/language/transformer.py`)

`ExpressionOperand` is already parsed by the grammar but hits a fatal error in `transformer.py:101`.
Implement a recursive evaluator supporting:

- Operators: `+`, `-`, `*`, `/`, `%`, `<<`, `>>`, `&`, `|`, `^`, `~`
- Operands: numeric literals and `define`/`EQU` constants
- Returns an `ImmediateOperand` with the computed value

This removes hacks like `add z, %ximm; add z, %ximm` (multiply-by-2 workaround) and makes
writing position-sensitive VRAM math much cleaner.

- **Files**: `jasm/language/transformer.py`, `jasm/language/ir/operands.py`

---

## Phase E: Demo Applications

These are user programs assembled with `org 0x4000` and loaded from disk via `exec`. They use
syscalls for all kernel interaction.

### E.1 — Word processor (`apps/editor.jasm`)

A full-screen text editor for reading and writing plain text files.

Features:

- Load a file from disk by name (passed as argument via convention TBD)
- Display file contents in the 80x25 VRAM grid, with line wrapping
- Cursor navigation: arrow keys move within the text buffer
- Insert and delete characters
- Save to disk on command (e.g., Ctrl+S)
- Exit and return to shell (e.g., Ctrl+Q)

The text buffer lives in user program memory (above 0x4000). Files are read via the `read_file`
syscall. Saving uses `write_file`.

Markdown-like rendering (bold, italic) is a stretch goal — the VRAM color attribute byte can
encode text color, so headers could display in a different color than body text.

### E.2 — Assembly editor / REPL (`apps/asm.jasm`)

A combined text editor and in-memory assembler. The user types assembly code, presses a key to
assemble, and the assembled binary is executed immediately.

This requires a minimal assembler implemented in JASM itself — a significant but achievable
project. A simpler first version could just be a hex editor that writes words directly to a
scratchpad region and jumps to it.

Phased approach:

1. **Hex editor**: type hex values, write them to a scratch buffer at `0x8000`, execute.
2. **Macro assembler**: parse a small subset of JASM syntax (MOV, JMP, CALL, RET, basic ALU),
   assemble to the scratch buffer, execute.

---

## Phase F: Physical Hardware

**Goal**: Everything above should be feasible to implement in hardware.

### Design principles

- **Port-mapped I/O only**. No memory-mapped I/O, no DMA bus master. Every device interaction
  goes through `INB`/`OUTB`. This keeps the address bus simple.
- **Interrupt-driven peripherals**. Devices signal completion via an IRQ line; the CPU polls a
  status port only when needed (e.g., RTC).
- **16-bit word-addressed memory**. SRAM chips are the natural fit (e.g., 128K×8 pairs used as
  128K×16). No DRAM complexity.

### Hardware device candidates

| Device           | Emulator                    | Physical candidate                            |
| ---------------- | --------------------------- | --------------------------------------------- |
| CPU              | `jaide/emulator.py`         | Custom FPGA or TTL discrete logic             |
| ROM              | `memory[0x0000-0x01FF]`     | Small EEPROM (AT28C16 or similar)             |
| RAM              | `memory[0x0200-0xFDFF]`     | SRAM (62256 or similar)                       |
| VRAM             | `banks[1]`                  | Dedicated SRAM bank, read by video controller |
| Video controller | `jaide/devices/graphics.py` | FPGA with VGA output                          |
| Keyboard         | `jaide/devices/keyboard.py` | PS/2 decoder (ATmega or discrete)             |
| Timer (PIT)      | `jaide/devices/pit.py`      | 8253/8254 PIT chip, or 555 + counter          |
| RTC              | `jaide/devices/rtc.py`      | DS1307 (I²C, needs small glue logic)          |
| Disk controller  | `jaide/devices/disk.py`     | SD card module over SPI + port decoder        |

The disk controller is the most interesting physical design challenge. The emulator's model
(sector-addressed, port-mapped, one-word-per-tick DMA, completion interrupt) maps directly onto
a microcontroller (e.g., ATmega328) acting as an SPI SD card bridge: the host CPU writes the
sector number and destination address to ports, the bridge reads from the SD card over SPI and
writes words into shared SRAM, then asserts an IRQ line when done.

### What is explicitly out of scope for physical hardware

- **MMU / memory protection**: not feasible without radical architecture changes.
- **Virtual memory / paging**: same.
- **Multiple privilege levels**: not needed for a single-user system.

---

## Execution order and dependencies

```txt
Phase A (Disk Controller) ─────────────────────── CRITICAL PATH
  A.1  disk.py device
  A.2  --disk CLI arg, emulator wiring
  A.3  kernel disk subroutines + disk interrupt handler
  A.4  mount + list commands work
       │
Phase B (EXEC + Syscalls) ─────────────────────── CRITICAL PATH
  B.1  memory map + executable format decided
  B.2  INT 0x10 syscall handler in kernel
  B.3  exec shell command
       │
    ┌──┴───────────────────────────────┐
Phase C (Shell UX)              Phase D (Assembler)
  C.1  display scrolling          D.1  expression evaluator
  C.2  input line management
  C.3  built-in commands
    └──┬───────────────────────────────┘
       │
Phase E (Applications) ─────────────────── depends on B + C
  E.1  word processor
  E.2  assembly editor / hex editor

Phase F (Physical Hardware) ────────────── parallel, ongoing
  informed by all prior phases
```

---

## Verification milestones

| Milestone    | Pass condition                                                                                                                                              |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A done**   | `make test`, then run emulator with `--disk disk.img -g`; type `mount`, see JFS header info; type `list`, see filenames from the image                      |
| **B done**   | Assemble a trivial "hello world" user program to `org 0x4000`, add it to the disk image, type `exec hello` in the shell, see output, return to shell prompt |
| **C done**   | Fill the shell with 30+ lines of output, verify scrolling; input line remains usable throughout                                                             |
| **D done**   | Assemble a program using constant arithmetic expressions (e.g., `mov a, VRAM_BASE + 80 * 2`), verify correct binary output                                  |
| **E.1 done** | Open a text file from disk in the editor, make edits, save, re-open, verify changes persisted                                                               |
| **E.2 done** | Type a small JASM program in the editor, assemble and execute it, verify behavior without leaving the OS                                                    |

---

## What is intentionally out of scope

- **Linker**: single-file assembly with `import` is sufficient for all target applications.
  Multi-module builds are a future "Phase G" if ever needed.
- **Privilege levels / supervisor mode**: not needed for a single-user emulated system.
- **Virtual memory / paging**: not feasible without radical architecture changes.
- **Mouse, audio, networking**: not needed for the target demo applications.
- **The OS filesystem itself written in assembly**: the JFS tool (`python -m jfs`) fills this
  role from the host side. On-device file creation/deletion can be added later.

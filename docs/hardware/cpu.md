# jaide: a 16-bit computing system architecture

## overview

- load-store, little-endia, von-neumann architecture
- 16-bit address bus touches 128Kib of word-addressable memory (~64k unique words, more with banking)
- fixed-width instructions with optional 16-bit immediates
- 16-bit word length
- 12 registers: 8 general-purpose, 4 special, all 16-bit

## programming jaide

jaide is programmed with `jasm`. jasm is a custom assembly language. it has a custom assembler that produces binaries unique to jaide's architecture.

see the [language specification](lang.md) for more information.

the full grammar used for lexical analysis is contained in [jasm/language/grammar.py](../jasm/language/grammar.py).

## how to run your code

jasm files use the `.jasm` file extension. Compile your code with `python -m jasm <source> -o <output>`.

once assembled to a binary file, run your code with `python -m emulator <binary>`.

for now, binaries are simply a raw memory image.

in the jaide emulator, type help to view a list of commands.

## reset state

on reset, general-purpose registers, flags, `mb`, and `pc` are `0x0000`.
`sp` and the protected supervisor stack pointer are `0xfdff`. the cpu starts in
supervisor mode with no active kernel event. the contents of ram are undefined
and rom is not modified.

execution starts at `0x0000`.

## registers

the jaide architecture supports up to 16 registers. all registers contain 16 bits.

_currently, 8 general purpose and 4 special registers are implemented. the four unused registers are reserved for future floating-point support._

### general purpose registers

`A`, `B`, `C`, `D`, `E`, `X`, `Y`, and `Z`.

### special registers

`PC` program counter _(read-only)_

`SP` stack pointer

`MB` memory bank

`F` flags _(zero, carry, negative, overflow)_

the format of the flags register is `C Z N O - - - - - - - - - - - -`.

## instructions

instructions are 16 bits long (two bytes, little endian), and may contain a 16-bit immediate located directly after them.

a single 16-bit instruction word is defined as follows:

`CCCC DDDD` `AAAAAAAA` `EEEEEEEE` `EEEEEEEE`

`AAAAAAAA` defines the opcode of the instruction (bits 8-15 of the word). the opcode implies an addressing mode.

`CCCC` defines a source or address register (bits 0-3 of the word).

`DDDD` defines a destination register (bits 4-7 of the word).

`EEEEEEEE` `EEEEEEEE` defines an immediate, address, or offset.

_all 16-bit values are little-endian: `LLLLLLLL` `HHHHHHHH` when represented as an immediate._

### instruction set

see the [instruction set](lang/inst.txt) for a comprehensive list of instructions

## memory

jaide supports up to 128 Kib of memory.

| Range             | Size      | Purpose                                      |
| ----------------- | --------- | -------------------------------------------- |
| `0xFF00...0xFFFF` | 512 bytes | reserved                                     |
| `0xFE00...0xFEFF` | 512 bytes | memory-mapped I/O                            |
| `0xFD00...0xFDFF` | 512 bytes | stack (recommended)                          |
| `0xB000...0xFCFF` | ~39 KiB   | reserved (future kernel heap / expansion)    |
| `0x7000...0xAFFF` | 32 KiB    | user processes RAM (banked)                  |
| `0x6000...0x6FFF` | 8 KiB     | filesystem block cache                       |
| `0x5000...0x5FFF` | 8 KiB     | kernel data (vars, FD table, disk scratch)   |
| `0x4000...0x4FFF` | 8 KiB     | video memory                                 |
| `0x0100...0x3FFF` | ~16 KiB   | kernel code                                  |
| `0x0000...0x00FF` | 512 bytes | BIOS ROM                                     |

_the stack grows downwards. reset initializes SP to 0xFDFF._

_banked memory can be swapped using the MB register._

ROM is protected from writes (`PUT 0x0080, A` will simply `NOP`, as will `PUSH` if SP points to ROM; but you have bigger problems if SP points to ROM!)

### memory banking

there are up to 31 banked memory regions (`MB = 1` through `MB = 31`). each maps the window `0x7000`–`0xAFFF` to a separate 16,384-word (2¹⁴) bank. `MB = 0` uses flat (unbanked) addressing for all regions except the bank window.

VRAM lives at `0x4000`–`0x4FFF` in flat memory and is not banked. user programs are loaded at `0x7000` in their assigned bank; the entry point is `0x7000`.

### the stack

`PUSH` and `POP` put/get a word from the stack.

`CALL` and `RET` utilize the stack to store a return address.

stack overflow/underflow behaviour is undefined.

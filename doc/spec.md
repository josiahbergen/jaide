# jaide: a 16-bit computing system architecture

## overview

- 32 instructions
- 16-bit word length
- 16-bit address bus touches 128k of word-addressable memory (more with banking)
- 12 registers (7 general-purpose, 5 special), all 16-bit
- load-store, little-endian, von-neumann architecture

## programming jaide

jaide is programmed with `jasm`. jasm is a custom assembly language. it has a custom assembler that produces binaries unique to jaide's architecture.

see the [language specification](lang.md) for more information.

the full grammar used for lexical analysis is contained in [jasm/language/grammar.py](../jasm/language/grammar.py).

## how to run your code

jasm files use the `.jasm` file extension. Compile your code with `python -m jasm <source> -o <output>`.

once assembled to a binary file, run your code with `python -m jaide <binary>`.

for now, binaries are simply a raw memory image.

in the jaide emulator, type help to view a list of commands.

## reset state

on reset, the content of all* registers is `0x0000`. the contents of RAM are undefined. ROM is not modified.

_*it is recommended that SP be set to 0xFEFF on reset._

## registers

the jaide architecture supports up to 16 registers. all registers contain 16 bits.

_currently, 7 general purpose and 5 special registers are implemented. the four unused registers are reserved for future floating-point support._

### general purpose registers

`A`, `B`, `C`, `D`, `E`, `X`, and `Y`.

### special registers

`PC` program counter _(read-only)_

`SP` stack pointer

`MB` memory bank

`F` flags _(zero, carry, negative, overflow, interrupts enabled)_

the format of the flags register is `C Z N O I - - - - - - - - - - -`.

`Z` zero _(read-only, always equal to 0x0000)_

## instructions

jaide uses a little-endian instruction format. instructions are 16 bits (two bytes) long, and may contain a 16-bit immediate located directly after them.

a single 16-bit instruction word is defined as follows: 

`CCCC DDDD` `AAAAAA BB` `EEEEEEEE` `EEEEEEEE`

`AAAAAA` defines the opcode of the instruction (bits 8-13 of the word).

`BB` defines the addressing mode of the source operand (bits 14-15 of the word).

`CCCC` defines a source or address register (bits 0-3 of the word).

`DDDD` defines a destination register (bits 4-7 of the word).

`EEEEEEEE` `EEEEEEEE` defines an immediate, address, or offset _(little-endian, if applicable)_.

### addressing modes:

| value | notation | mode            |
| ----- | -------- | --------------- |
| 0     | reg      | register        |
| 1     | imm16*   | immediate       |
| 2     | [imm16]* | memory direct   |
| 3     | [reg]    | memory indirect |

_\*all 16-bit values are little-endian: `LLLLLLLL` `HHHHHHHH` when represented as an immediate._

### instruction set

see [inst.txt](inst.txt) for the full instruction set specification and encoding.

at this time, only 32 instructions are defined. jaide supports up to 64 unique instructions, and these will eventially all be implemented. 

## memory

| Range             | Size      | Purpose                        |
| ----------------- | --------- | ------------------------------ |
| `0xFEFF...0xFFFF` | 256 bytes | interrupt table                |
| `0xFDFF...0xFEFF` | 256 bytes | stack (recommended)\*\*        |
| `0xC000...0xFDFF` | 15 KiB    | general purpose RAM            |
| `0x8000...0xBFFF` | 16 KiB    | general purpose RAM (banked)\* |
| `0x0000...0x7FFF` | 32 KiB    | general purpose ROM            |

_\*this memory can be swapped using the MB register._

_\*\*the stack grows downwards. it is recommended that SP be set to 0xFEFF._

ROM is protected from writes (`PUT 0x0100, A` will simply `NOP`, as will `PUSH` if SP points to ROM).

### banking

there are up to 32 possible memory banks. MB = 0 indicates that the built-in RAM is in use. it is recommended that MB = 1 point to built-in VRAM.

### the stack

`PUSH` and `POP` put/get a word (2 bytes) from the stack.

SP must be a multiple of 2 to facilitate this. SP always points to the last used word.

stack overflow/underflow behaviour is undefined.

## interrupts

jaide supports up to 128 programmable interrupts.

interrupts 0 to 3 are reserved for hardware interrutps. a programmer must define handlers for each of them.

if a hardware interrupt is not handled, the unhandled fault interrupt will be called. if this is not handed, jaide will reset.

### hardware interrupts

| interrupt | description         |
| --------- | ------------------- |
| 0         | unhandled fault     |
| 1         | invalid instruction |
| 2         | protection fault    |
| 3         | reserved            |

### the INT and IRET instructions

when an interrupt `n` is called, jaide saves its state and transfers execution to the word found at the offset `n` into the interrupt table, starting at `0xFFFF` and moving downwards.

more specifically, when `INT` is called:

| action                      | description                                              |
| --------------------------- | -------------------------------------------------------- |
| `NOP if I == 0`             | if interrupts are masked, jaide will `NOP` and continue. |
| `[SP--] <- PC`              | program counter is pushed                                |
| `[SP--] <- F`               | flags are pushed                                         |
| `I <- 0`                    | ineterrupt mask is cleared                               |
| `vector = 0xFFFF - n`       | handler address is computed                              |
| `PC <- MEM16[vector]`       | execution jumps to handler                               |

nested interrupts can be allowed by setting `I` at the top of your interrupt handler.

normal execution can be restored by calling `IRET`. more specifically, when `IRET` is called:

| action           | description                                              |
| ---------------- | -------------------------------------------------------- |
| `F <- [SP++]`    | flags are popped (unmasks interrupts if applicable)      |
| `PC <- [SP++]`   | program counter is popped                                |

## i/o ports

ports can be used to interact with I/O devices. The INB and OUTB instructions exist to facilitate this. jaide supports up to 256 I/O devices.

all ports have 16-bit data widths. there currently exists no standard for communication to/from jaide's ports.

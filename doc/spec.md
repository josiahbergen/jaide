# jaide: a 16-bit computing system architecture

## overview

- 32 instructions (with support for up to 64)
- 16-bit word length
- 16-bit address bus touches 128Kib of word-addressable memory (~64k unique values, more with banking)
- 12 registers: 8 general-purpose, 4 special, all 16-bit
- load-store, little-endian, interrupt-driven, von-neumann architecture

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

`A`, `B`, `C`, `D`, `E`, `X`, `Y`, and `Z`.

### special registers

`PC` program counter _(read-only)_

`SP` stack pointer

`MB` memory bank

`F` flags _(zero, carry, negative, overflow, interrupts enabled)_

the format of the flags register is `C Z N O I - - - - - - - - - - -`.

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

_\*\*the stack grows downwards. it is recommended that SP be set to 0xFEFF._

_\*this memory can be swapped using the MB register._

ROM is protected from writes (`PUT 0x0100, A` will simply `NOP`, as will `PUSH` if SP points to ROM).

### memory banking

there are up to 32 possible memory banks. `MB = 0` indicates that the built-in RAM is in use. it is recommended that MB = 1 point to built-in VRAM.

### the stack

`PUSH` and `POP` put/get a word from the stack.

`CALL` and `RET` utilize the stack to store a return address.

stack overflow/underflow behaviour is undefined.

## interrupts

jaide supports up to 256 interrupt vectors. these can be triggered programatically, by external devices, or by the cpu itself.

### hardware interrupts

jaide checks the `IRQ` (interrupt reqest) line at the end of every instruction cycle, before the next fetch. if `IRQ` is high and the interrupt flag is set:

1. jaide sets the `INTA` (interrupt acknowledge) line high, and waits.

2. the external device places a desired 16-bit interrupt vector on the data bus. `IRQ` is cleared to communicate that the the vector is ready.

3. the cpu reads the vector, clears `INTA`, and proceeds with the standard interrupt procedure (see below)

interrupts 0 to 3 are reserved for hardware interrutps. a programmer may define handlers for each of them.

### vector allocation
 
| vector | type      |	description                            |
| ------ | --------- | ----------------------------------------|
| 0	     | exception | unhandled fault                         |
| 1	     | exception | invalid instruction                     |
| 2	     | exception | protection fault                        |
| 3	     | reserved	 | reserved                                |
| 4-127  | external  | available for external hardware devices |

### a note on HALT

calling `HALT` puts the cpu in a *non-permanent*, low-power idle state. the cpu will wait in this state until an enabled interrupt occurs. when the interrupt returns (see below), excecution will resume after the `HALT` instruction.

### using INT and IRET

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

## ports

ports can be used to interact with external i/o devices. The `INB` and `OUTB` instructions exist to facilitate this. jaide supports up to 255 custom i/o devices.

all ports have 16-bit data widths. it is recommended that a programmer makes use of the interrupt system, and then uses the i/o instructions to communicate data

### system interface

port `0xFF` is a special port that can be used to control the physical hardware.

the system interface port supports these commands:

| value   | command     | emulator behavior            | hardware behavior    |
| ------- | ----------- | ---------------------------- | -------------------- |
| 0x00    | nop         | do nothing                   | do nothing           |
| 0x01    | reset       | clear ram/regs, set pc = 0   | pull reset pin low   |
| 0x02    | halt        | set halted = true            | stop the clock       |
| 0x03    | nop         | shut down emulator process   | disconnect power     |
| other   | _undefined_ | _undefined_                  | _undefined_          |

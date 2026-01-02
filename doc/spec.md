# JAIDE8 SPECIFICATION

Meet JAIDE8: A custom CPU architecture design with a custom everything.

## Features

- 32 instructions (8 addressing modes)
- 8-bit data width
- 16-bit address bus (64k of accessable memory)
- Memory banking
- Device communication through built-in CPU instructions

## Programming JAIDE8

JAIDE8 is programmed with `JASM`. JASM is a custom assembly language.

It has a custom assembler that produces binaries unique to JAIDE8's architecture.

See the [language specification](lang.md) for more information.

The full Lark grammar used for lexical analysis is contained in [asm/util.py](../asm/util.py).

## How to Run Your Code

JASM files use the `.jasm` file extension. Compile your code with `python jasm.py hello.jasm -o hello.bin`.

Once assembled to a binary file, run your code with `python emulator.py hello.bin`.

## Emulator

The emulator allows you to run compiled binaries and inspect the CPU state.

Usage: `python emulator.py [binary]`

REPL commands:

- `load <path>`: Load a binary file into memory
- `step`: Execute one instruction
- `cont`: Continue execution until a breakpoint or halt
- `run`: Run until halt
- `break <hex>`: Set a breakpoint at address
- `regs`: Display register values
- `mem <hex> <len>`: Display memory contents
- `disasm [addr]`: Disassemble instruction at address (or PC)
- `ports`: Display non-zero port values
- `quit`: Exit the emulator

## Instruction Set Reference

| OPCODE | MNEMONIC | OPERAND 1 | OPERAND 2       | DESCRIPTION                  | OPERATION                                         |
| ------ | -------- | --------- | --------------- | ---------------------------- | ------------------------------------------------- |
| 0      | LOAD     | reg       | [imm16/reg:reg] | load 8-bit value from memory | reg <- [imm16/reg:reg]                            |
| 1      | STORE    | reg       | [imm16/reg:reg] | store 8-bit value to memory  | [imm16/reg:reg] <- reg                            |
| 2      | MOVE     | reg       | reg/imm8        | move 8-bit value             | reg <- reg/imm8                                   |
| 3      | PUSH     | reg/imm8  |                 | push to stack                | [SP--] <- imm8/reg                                |
| 4      | POP      | reg       |                 | pop from stack               | reg <- [++SP]                                     |
| 5      | ADD^     | reg       | reg/imm8        | add                          | reg <- reg + (imm8/reg)                           |
| 6      | ADDC^    | reg       | reg/imm8        | add with carry               | reg <- reg + (imm8/reg)                           |
| 7      | SUB^     | reg       | reg/imm8        | subtract                     | reg <- reg - (imm8/reg)                           |
| 8      | SUBB^    | reg       | reg/imm8        | subract with borrow          | reg <- reg - (imm8/reg)                           |
| 9      | INC      | reg       |                 | increment                    | reg <- reg + 1                                    |
| 10     | DEC      | reg       |                 | decrement                    | reg <- reg - 1                                    |
| 11     | SHL      | reg       | reg/imm8        | bit shift left               | reg <- reg << (reg/imm8)                          |
| 12     | SHR      | reg       | reg/imm8        | bit shift right              | reg <- reg >> (reg/imm8)                          |
| 13     | AND      | reg       | reg/imm8        | bitwise and                  | reg <- reg AND (reg/imm8)                         |
| 14     | OR       | reg       | reg/imm8        | bitwise or                   | reg <- reg OR (reg/imm8)                          |
| 15     | NOR      | reg       | reg/imm8        | bitwise nor                  | reg <- reg NOR (reg/imm8)                         |
| 16     | NOT      | reg       |                 | bitwise not                  | reg <- reg NOR (reg/imm8)                         |
| 17     | XOR      | reg       | reg/imm8        | bitwise xor                  | reg <- reg XOR (reg/imm8)                         |
| 18     | INB      | reg       | port(reg/imm8)  | get byte from I/O port       | reg <- port(reg/imm8)                             |
| 19     | OUTB     | reg       | port(reg/imm8)  | send byte through I/O port   | port(reg/imm8) <- reg                             |
| 20     | CMP^     | reg       | reg/imm8        | compare                      | Z, C, B <- reg - reg/imm8                         |
| 21     | SEC      |           |                 | set carry flag               | carry flag <- 1                                   |
| 22     | CLC      |           |                 | clear carry flag             | carry flag <- 0                                   |
| 23     | CLZ      |           |                 | clear zero flag              | zero flag <- 0                                    |
| 24     | JMP      | [imm16]   |                 | unconditional jump           | PC <- [imm16/reg:reg]                             |
| 25     | JZ       | [imm16]   |                 | jump if zero                 | PC <- [imm16/reg:reg] if zero flag is 1 else NOP  |
| 26     | JNZ      | [imm16]   |                 | jump of not zero             | PC <- [imm16/reg:reg] if zero flag is 0 else NOP  |
| 27     | JC       | [imm16]   |                 | jump if carry                | PC <- [imm16/reg:reg] if carry flag is 1 else NOP |
| 28     | JNC      | [imm16]   |                 | jump if not carry            | PC <- [imm16/reg:reg] if carry flag is 0 else NOP |
| 29     | INT\*    | imm8      |                 | call an interrupt            | NOP (to be added later)                           |
| 30     | HALT\*   |           |                 | halt                         | halted flag <- 1                                  |
| 31     | NOP      |           |                 | no operation                 | n/a                                               |

^ These instructions modify the flags register. <br> \* These instructions modify the status register.

## Instruction Format

Instruction format is `AAAAA BBB` `CCCC DDDD` `EEEE EEEE*` `FFFFFFFF*` where:

`AAAAA` is the instruction operand code and `BBB` is the addressing mode.

`BBB` defines what `CCCC`, `DDDD`, `EEEE EEEE`, and `FFFFFFFF` contain (or if they are utilized at all).

- `000`: No operands.
- `001`: `CCCC` defines a single register argument. `DDDD EEEEEEEEE FFFFFFFF` are unused.
- `010`: `EEEEEEEE` defines an 8-bit immediate. `CCCC DDDD` and `FFFFFFFF` are unused.
- `011`: `CCCC` and `DDDD` define a first and second register argument, respectively. `EEEEEEEE FFFFFFFF` are unused.
- `100`: `CCCC` defines a register argument. `EEEEEEE` defines an 8-bit immediate. `DDDD` is unused.
- `101`: `CCCC` defines a single register argument. `EEEEEEEE FFFFFFFF` defines a memory location. `DDDD` is unused.
- `110`: `CCCC` defines a single register argument. `EEEE EEEE` (`LLLL HHHH`) defines a register pair which is interpreted as a memory location.
- `111`: `EEEEEEEE FFFFFFFF` defines a 16-bit immediate. `CCCC DDDD` are unused.

_\* These bytes are not in all instructions. See the table below._

`BBB` also defines how many bytes an instruction takes up in memory:

| Value | Length | Type               | Description                                   |
| ----- | ------ | ------------------ | --------------------------------------------- |
| 000   | 1      | No operands        | _Really?_                                     |
| 001   | 2      | `REG`              | Register                                      |
| 010   | 3      | `IMM8`             | 8-bit Immediate                               |
| 011   | 2      | `REG, REG`         | Register / Register                           |
| 100   | 3      | `REG, IMM8`        | Register / 8-bit Immediate                    |
| 101   | 4      | `REG, [IMM16]`     | Register / Address as 16-bit Immediate\*      |
| 110   | 3      | `REG, [REG:REG]`   | Register / Address as Register Pair\*         |
| 111   | 4      | `[IMM16]`          | Address as 16-bit Immediate\* |

_\* All 16-bit values are little-endian: `LLLLLLLL HHHHHHHH` if represented as an immediate, `L:H` if represented as a register pair._

## Registers

There are six 8-bit general purpose registers:

| Index | Name | Purpose                        |
| ----- | ---- | ------------------------------ |
| 0     | A    | General purpose / accumulator  |
| 1     | B    | General purpose                |
| 2     | C    | General purpose                |
| 3     | D    | General purpose                |
| 4     | X    | Low address / general purpose  |
| 5     | Y    | High address / general purpose |

There are five memory-mapped registers (see Memory Layout below)

| Index | Name | Purpose                     |
| ----- | ---- | --------------------------- |
| 6     | F    | Flags                       |
| 7     | Z    | Zero                        |
| 8     | PC   | Program Counter (read-only) |
| 9     | SP   | Stack Pointer               |
| A     | MB   | Memory Bank                 |
| B     | STS  | Status                      |

### Flags Register

The bytes of the Flags register is defined as follows:

```
0: Carry
1: Zero
2: Negative
3: Overflow
Bytes 5-7 are reserved for future use.
```

### Status Register

The bytes of the Status register is defined as follows:

```
0: Error
1: Halted
Bytes 2-7 are reserved for future use.
```

## Memory Layout

Total addressable memory: `64Kib`

The memory layout is as follows:

| Range          | Size      | Purpose                                         |
| -------------- | --------- | ----------------------------------------------- |
| 0x0000..0x7FFF | 32 KiB    | General Purpose ROM                             |
| 0x8000..0xBFFF | 16 KiB    | General Purpose RAM (banked)\*                  |
| 0xC000..0xFDFF | 15 KiB    | General Purpose RAM                             |
| 0xFC00..0xFEFF | 768 bytes | Stack (recommended)\*\*                         |
| 0xFF00..0xFFF8 | 249 bytes | Scratch                                         |
| 0xFFF9..0xFFF9 | 1 byte    | Flags register(mapped)                          |
| 0xFFFA..0xFFFA | 1 byte    | Zero register(mapped)                           |
| 0xFFFB..0xFFFB | 1 byte    | Memory Bank register (mapped)                   |
| 0xFFFC..0xFFFD | 2 bytes   | Stack Pointer (mapped, 16 bits little-endian)   |
| 0xFFFE..0xFFFF | 2 bytes   | Program Counter (mapped, 16 bits little-endian) |

_\* This memory can be swapped using the MB register. MB = 0 indicates that the built-in RAM is in use. It is recommended that MB = 1 point to the built-in VRAM._

_\*\* The stack grows downwards. It is recommended that SP = 0xFEFF._

## Ports

Ports can be used to interact with I/O devices. The INB and OUTB exist to facilitate this. JAIDE8 supports up to 256 I/O devices.

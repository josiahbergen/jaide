# jaide: a 16-bit computing system architecture

## overview

- 32 instructions
- 16-bit data width
- 16-bit address bus (with plans for a 32-bit extension)
- 7 general-purpose 16-bit registers and 5 special registers
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

on reset, the contents of all registers is `0x0000`. the contents of RAM are undefined. ROM is not modified.

## registers

the jaide architecture supports up to 16 registers. all registers contain 16 bits.

_currently, 7 general purpose and 5 special registers are implemented. the four unused registers are reserved for future floating-point support._

### general purpose registers

`A`, `B`, `C`, `D`, `E`, `X`, and `Y`.

### special registers

`PC` program counter _(read-only)_

`SP` stack pointer

`MB` memory bank

`F` flags _(zero, carry, negative (unused), overflow, interrupts enabled)_

the format of the flags register is `C Z N O I - - - -`.

`Z` zero _(read-only, value is always 0x0000)_

## instruction format

instructions are 16 bits long, and may contain a 16-bit immediate immediately (ha) after them.

the format of an instruction is as follows: `AAAAA BBB` `CCCC DDDD` `EEEEEEEE` `EEEEEEEE`

`AAAAA` defines the opcode of the instruction.

`BBB` defines what the next bits in the instruction contain.

`CCCC` and `DDDD` define register operands _(if applicable)_.

`EEEEEEEE` `EEEEEEEE` defines a 16-bit immediate value _(little-endian, if applicable)_.

the value encoded in `BBB` defines these isntruction formats:

| value | operands     | defined bytes                          |
| ----- | ------------ | -------------------------------------- |
| 0     | no operands  | `XXXXX 000 ---- ---- ----------------` |
| 1     | reg          | `XXXXX 001 XXXX ---- ----------------` |
| 2     | imm16\*      | `XXXXX 010 ---- ---- XXXXXXXXXXXXXXXX` |
| 3     | reg, reg     | `XXXXX 011 XXXX XXXX ----------------` |
| 4     | reg, imm16\* | `XXXXX 100 XXXX ---- XXXXXXXXXXXXXXXX` |
| 5     | [reg]^       | `XXXXX 101 XXXX ---- ----------------` |
| 6     | _reserved_   | `----- 110 ---- ---- ----------------` |
| 7     | _reserved_   | `----- 111 ---- ---- ----------------` |

_\*all 16-bit values are little-endian: `LLLLLLLL HHHHHHHH` when represented as an immediate value._

_^all addresses are absolute. [reg] is defined as "the address contained inside reg", i.e. reg dereferenced_

## instruction set

| OPCODE | MNEMONIC | OPERAND 1       | OPERAND 2       | DESCRIPTION                   | OPERATION                                      |
| ------ | -------- | --------------- | --------------- | ----------------------------- | ---------------------------------------------- |
| 0      | LOAD     | reg             | [imm16/reg]     | load 16-bit value from memory | reg <- [imm16/reg]                             |
| 1      | STORE    | [imm16/reg]     | reg             | store 16-bit value to memory  | [imm16/reg] <- reg                             |
| 2      | MOVE     | reg             | reg/imm16       | move 16-bit value             | reg <- reg/imm16                               |
| 3      | PUSH     | reg/imm16       |                 | push to stack                 | [SP--] <- imm16/reg                            |
| 4      | POP      | reg             |                 | pop from stack                | reg <- [++SP]                                  |
| 5      | ADD^     | reg             | reg/imm16       | add                           | reg, Z, C, O <- reg + (imm16/reg)              |
| 6      | ADC^     | reg             | reg/imm16       | add with carry                | reg, Z, C, O <- reg + (imm16/reg) + C          |
| 7      | SUB^     | reg             | reg/imm16       | subtract                      | reg, Z, C, O <- reg - (imm16/reg)              |
| 8      | SBC^     | reg             | reg/imm16       | subtract with borrow          | reg, Z, C, O <- reg - (imm16/reg) - C          |
| 9      | INC      | reg             |                 | increment                     | reg, Z, C, O <- reg++                          |
| 10     | DEC      | reg             |                 | decrement                     | reg, Z, C, O <- reg--                          |
| 11     | SHL      | reg             | reg/imm16       | bit shift left                | reg, Z, C, O <- reg << (reg/imm16)             |
| 12     | SHR      | reg             | reg/imm16       | bit shift right               | reg, Z, C, O <- reg >> (reg/imm16)             |
| 13     | AND      | reg             | reg/imm16       | bitwise and                   | reg, Z <- reg & (reg/imm16)                    |
| 14     | OR       | reg             | reg/imm16       | bitwise or                    | reg, Z <- reg \| (reg/imm16)                   |
| 15     | NOR      | reg             | reg/imm16       | bitwise nor                   | reg, Z <- reg ~\| (reg/imm16)                  |
| 16     | NOT      | reg             |                 | bitwise not                   | reg, Z <- ~reg                                 |
| 17     | XOR      | reg             | reg/imm16       | bitwise xor                   | reg, Z <- reg ^ (reg/imm16)                    |
| 18     | INB      | reg             | port(reg/imm16) | get word from I/O port        | reg, Z <- port(reg/imm16)                      |
| 19     | OUTB     | port(reg/imm16) | reg             | send word through I/O port    | port(reg/imm16) <- reg                         |
| 20     | CMP^     | reg             | reg/imm16       | compare                       | Z, C <- reg - reg/imm16                        |
| 21     | JMP      | imm16/reg       |                 | unconditional jump            | PC <- [imm16/reg]                              |
| 22     | JZ       | imm16/reg       |                 | jump if zero                  | PC <- [imm16/reg] if Z == 1 else NOP           |
| 23     | JNZ      | imm16/reg       |                 | jump of not zero              | PC <- [imm16/reg] if Z == 0 else NOP           |
| 24     | JC       | imm16/reg       |                 | jump if carry                 | PC <- [imm16/reg] if C == 1 else NOP           |
| 25     | JNC      | imm16/reg       |                 | jump if not carry             | PC <- [imm16/reg] if C == 0 else NOP           |
| 26     | CALL     | imm16/reg       |                 | call a function               | [SP--] <- imm16/reg + 1, pc <- imm16/reg       |
| 27     | RET      |                 |                 | return from a function        | pc <- [++SP]                                   |
| 28     | INT      | imm16           |                 | call an interrupt             | [SP--] <- imm16/reg + 1, pc <- int(imm16), I++ |
| 29     | IRET     |                 |                 | return from an interrupt      | pc <- [SP++], I-- if I > 0 else NOP            |
| 30     | HALT     |                 |                 | halt                          | halted flag <- 1                               |
| 31     | NOP      |                 |                 | no operation                  | n/a                                            |

^ These instructions modify the flags register.

## memory

| Range             | Size      | Purpose                        |
| ----------------- | --------- | ------------------------------ |
| `0xFEFF...0xFFFF` | 256 bytes | interrupt table                |
| `0xFDFF...0xFEFF` | 256 bytes | stack (recommended)\*\*        |
| `0xC000...0xFDFF` | 15 KiB    | general purpose RAM            |
| `0x8000...0xBFFF` | 16 KiB    | general purpose RAM (banked)\* |
| `0x0000...0x7FFF` | 32 KiB    | general purpose ROM            |

_\*this memory can be swapped using the MB register._

_\*\*the stack grows downwards. it is recommended that SP = 0xFEFF._

ROM is protected from writes (`STORE 0x0100, A` will simply `NOP`, as will `PUSH` if SP points to ROM).

### banking

there are up to 256 possible memory banks. MB = 0 indicates that the built-in RAM is in use. it is recommended that MB = 1 point to built-in VRAM.

### the stack

`PUSH` and `POP` put/get a word (2 bytes) from the stack.

SP must be a multiple of 2 to facilitate this. SP always points to the last used word.

stack overflow/underflow behaviour is undefined.

## interrupts

jaide supports up to 128 interrupts.

when an interrupt `n` is called, jaide saves it's state and transfers execution to the address found at the offset `2n` into the interrupt table, starting at `0xFFFF` and moving downwards.

more specifically, when `INT` is called:

| action                        | description                                              |
| ----------------------------- | -------------------------------------------------------- |
| `PC++ if I == 0`              | if interrupts are masked, jaide will `NOP` and continue. |
| `[SP--] <- PC`                | program counter is pushed                                |
| `[SP--] <- F`                 | flags are pushed                                         |
| `I <- 0`                      | ineterrupt mask is cleared                               |
| `vector = 0xFFFF - (n \* 2)`  | handler address is computed                              |
| `PC <- MEM16[vector_address]` | execution jumps to handler                               |

nested interrupts can be allowed by setting `I` at the top of your interrupt handler.

normal execution can be restored by calling `IRET`.

more specifically, when `IRET` is called:

| action           | description                                              |
| ---------------- | -------------------------------------------------------- |
| `PC++ if I == 0` | if interrupts are masked, jaide will `NOP` and continue. |
| `F <- [SP++]`    | flags are popped (unmasks interrupts if applicable)      |
| `PC <- [SP++]`   | program counter is popped                                |

## i/o ports

ports can be used to interact with I/O devices. The INB and OUTB instructions exist to facilitate this. jaide supports up to 256 I/O devices.

all ports have 16-bit data widths. there currently exists no standard for communication to/from jaide's ports.

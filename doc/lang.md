# the jasm programming language

okay technically it's an assembly language but who's really asking

jasm is a custom assembly langauge that, when assembled, allows one to run binaries on the jaide architecture.

to make programming easier, extensions for [vscode](https://github.com/josiahbergen/jasm), [cursor](https://github.com/josiahbergen/jasm), and [zed (outdated, contact me if you need it)](https://github.com/josiahbergen/zed-jasm) are available.

for a list of all instructions, see the [instruction set](lang/inst.txt). you can also view the language [grammar](../jasm/language/grammar.py), if you're into that.

_keep in mind that proficiency in at least one assembly language (x86 perferred!) is assumed when reading this document. jasm is very similar to other assembly programming languages, and you will find that most aspects come naturally!_

## basics

```jasm
start:
    ; write comments with the ";" charater!

    mov a, 0x10 ; move immediate 0x10 into register a
    put a, 0xC000 ; put contents of register a into memory location 0xC000

    cmp A, B ; compare registers A and B
    jz equal ; jump if zero (equal)
    halt ; they were not equal, halt

equal:
    ; they were equal! great!
    add A, 0xf0 ; do some math
    halt
```

## assembly

the jasm assembler supports the following flags:

`python -m jasm source [--output OUTPUT] [--nowarn] [--nowrite] [--nolink] [--verbosity VERBOSITY] [-h]`

| flag      | effect                                                       |
| --------- | ------------------------------------------------------------ |
| source    | the source file to assemble                                  |
| output    | the output file path (defaults to a.bin)                     |
| nowarn    | suppress warnings                                            |
| nowrite   | suppress writing to output files                             |
| nolink    | resolve labels as absolute addresses (makes code unlinkable) |
| verbosity | set verbosity (accepts values from 0-3)                      |

`--nolink` should be used for any code that will be loaded at a fixed, known address (bootloader, kernel, interrupt handlers). labels resolve to their absolute address as computed from the `org` directive. the assembled binary is only correct when loaded at that address.

_note: linkable (position-independent) code is not yet implemented. `--nolink` is currently the only supported mode._

## constants

numbers can be expressed in base `2`, `10`, or `16`. standard prefixes are used.

strings (only valid in data directives, see below) must be encased in quotes (`"`).

## addressing modes

jasm uses the following addressing modes:

| mode             | syntax   | where does the value come from?  |
| ---------------- | -------- | -------------------------------- |
| register         | `a`      | register value                   |
| immediate        | `0x1000` | immediate value                  |
| register pointer | `[a]`    | memory at address in register    |

when used in an instruction operand, a label name resolves to its absolute address (a 16-bit immediate). use `org` to set the base address.

```jasm
org 0x0000
mov b, my_label     ; loads the absolute address of my_label into b
jmp my_label        ; jumps to the absolute address of my_label
put [d], my_label   ; stores the absolute address of my_label into memory at [d]
```

conditional branch instructions (`jz`, `jnz`, `jc`, etc.) use a pc-relative offset internally, but you write them the same way — the assembler computes the offset for you.

_note: PIC (position-independent) addressing modes (`[label]`, `[label + reg]`) are reserved for a future linker design and are not currently supported._

## devices

jaide's emulator comes with a few devices out-of-the-box.

see the device [documentation](devices/) for information on each device!

## directives

### data

used to inline binary data into your program. gonna get deprecated/replaced with a data segment once I get segmentation working.

```jasm
; use a label to keep track of location
data_example:
    data 0x1111 ; 0x1111 will now live in memory at [data_example]

hello:
    data "hello, world!", 0 ; string literal
```

### import

import the contents of another jasm source file. works exactly like C's include (i.e. by pasting in raw file contents).

```jasm
import "libs/string.jasm"
```

### define

define a constant. must be a number.

```jasm
define vram_start 0x1000
mov x, vram_start ; compiles to 'mov x, 0x1000'
```

### times

fill a defined number of words with a value.

```jasm
times 512, 0x0000 ; generates 512 words of zeros
```

### align

pad code with zeros until the program counter is aligned to a boundary.

```jasm
align 0x200 ; if pc is 0x26, this will generate 472 words of zeros.
```

### org

set the origin/load address for label resolution. useful for code you don't want to (or can't) link.

```jasm
org 0x200
```

## macros

jasm supports powerful (using the term powerful _very_ loosely) macros. macro definitions live only in the assembler, they are not emitted as code or data.

macro bodies may only contain instructions, data, and labels. labels are name-mangled per expansion.

### definition

syntax:

```jasm
macro <name> [%param, %param ...]
    ...lines...
end macro
```

example macro definition:

```jasm
macro xy_to_vram %dest, %x, %y
    mov %dest, 0x0200 ; start of vram
    push %y ; save y value (we multiply this to get offset)
    mul %y, 80 ; get y offset to vram
    add %dest, %y
    add %dest, %x
    pop %y ; restore y value
end macro
```

### usage

call a macro like a mnemonic, with the macro name and a comma-separated operand list. the number and order of operands on the call must match the macro’s definition.

```jasm
mov x, 0
mov y, 10
xy_to_vram z, x, y ; puts some memory address in z
```

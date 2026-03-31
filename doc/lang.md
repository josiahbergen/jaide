
# the jasm programming language

okay technically it's an assembly language but who's really asking

to make programming easier, extensions for [vscode](https://github.com/josiahbergen/jasm), [cursor](https://github.com/josiahbergen/jasm), and [zed (outdated, contact me if you need it)](https://github.com/josiahbergen/zed-jasm)  are available.

for a list of all instructions, see the [instruction set](lang/inst.txt). you can also view the language [grammar](../jasm/language/grammar.py), if you're into that.

_keep in mind that proficiency in at least one assembly language (x86 perferred!) is assumed when reading this document. jasm is very similar to other assembly programming languages, and you will find that most aspects come naturally!_

## basics

```jasm
start:
    mov a, 0x10 ; move immediate 0x10 into register a
    put a, 0xC000 ; put contents of register a into memory location 0xC000

    cmp A, B ; compare registers A and B
    jz equal ; jump if zero (equal)
    hant ; they were not equal, halt

equal:
    ; they were equal! great!
    add A, 0xf0 ; do some math
    halt
```

## constants

numbers can be expressed in base `2`, `10`, or `16`. standard prefixes are used.

strings (only valid in data direcives, see below) must be encased in quotes (`"`).

## addressing modes

jasm uses six addressing modes. see the table below:

| mode              |  syntax     |  where does the value come from? |
| ----------------- | ----------- | -------------------------------- |
| register          | a           |  register value                  |
| immediate         | 0x1000      |  immediate value                 |
| relative          | label       |  value of pc + immediate         |
| register pointer  | [a]         |  memory at value in register     |
| offset pointer    | [label + a] |  memory at immediate + register  |
| relative pointer  | [label]     |  memory at pc + immediate        |

## directives

### data

used to inline binary data into your program. gonna get depricated/replaced with a data segment once I get segmentation working.

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

fill a defined number words with a value.

```jasm
times 512, 0x0000 ; generates 512 words of zeros
```

### align

pads code with zeros until the program counter is aligned to a boundary.

```jasm
align 0x200 ; if pc is 0x26, this will generate 472 words of zeros. 
```

### org

sets the origin/load address for label resolution. useful for code you don't want to (or can't) link.

```jasm
org 0x200
```

## macros

jasm supports powerful (using the term powerful very loosely) macros. macro definitions live only in the assembler. they are not emitted as code or data.

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

after expansion, the rest of the pipeline (labels, constants, encoding) sees the macro as if you had typed the expanded instructions yourself.

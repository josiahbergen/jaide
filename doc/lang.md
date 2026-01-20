
# jasm specification

to make programming easier, extensions for [VSCode](https://github.com/josiahbergen/jasm), [Cursor](https://github.com/josiahbergen/jasm), and [Zed](https://github.com/josiahbergen/zed-jasm) are available.

for a list of all instructions, see the table in the [spec](spec.md). you can also view the [language EBNF](ebnf.txt).

keep in mind that proficiency in at least one assembly language is assumed when reading this document. JASM is very similar to other assembly programming languages, and you will find that most aspects come naturally!

## The Basics

```jasm
start: ; label definition
    MOVE A, 0x10 ; move immediate 0x10 into register A
    STORE A, 0xC000 ; put contents of register A into memory location 0xC000

    CMP A, B ; compare registers A and B
    JZ equal ; jump if zero (equal)
    HALT ; they were not equal, halt

equal: ; they were equal! great!
    ADD A, 0xf0 ; do some math
    HALT
```

## Data

You can add raw data bytes to your assembled code. Binary, hex, decimal, and string literals are supported.

```jasm
data_example: ; use a label to keep track of the location
DATA 0x1111 ; 0x1111 will now live in memory at [data_example]

hello:
DATA "hello, world!", 0 ; putting a string literal in memory
```

## Macros

Macros are supported, as well as inline expressions.

```jasm
; a macro to check if some address is in rom
; puts 1 in A if the address is in ROM, 0 if it is in RAM
MACRO ISROM %address
    CMP %address, 0x8000
    MOV A, F
    AND A, b10000000
    RSH A, 7
END MACRO

; to invoke:
ISROM 0xC000 ; A <- 0
```

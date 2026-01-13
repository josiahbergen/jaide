
# JASM SPECIFICATION

To make programming easier, extensions for [VSCode](https://github.com/josiahbergen/jasm), [Cursor](https://github.com/josiahbergen/jasm), and [Zed](https://github.com/josiahbergen/zed-jasm) are available.

To see a list of all instructions, see the [instruction table](inst.txt). You can also view the [language EBNF](ebnf.txt).

Keep in mind that proficiency in at least one assembly language is assumed when reading this document. JASM is very similar to other assembly programming languages, and you will find that most aspects come naturally!

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
; a macro to load a 16-bit address into register pair X:Y
MACRO load_address %addr
    MOVE X, (%addr & 0x00FF) ; inline expressions are notated with parentheses
    MOVE Y, (%addr >> 4)
END MACRO

; to invoke:
load_address 0xC000 ; X <- 0x00, Y <- 0xC0

; we can now use the address in X:Y like so:
MOVE A, 0xFF
STORE A, X:Y ; note the register pair notation
```

That's it!

Nothing else is really defined yet, so check back for more detailed documentation soon!

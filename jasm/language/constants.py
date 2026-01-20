# language/constants.py
# language constants used by the assembler.
# josiah bergen, december 2025

from enum import Enum

OPCODES = {
    "HALT": 0,
    "LOAD": 1,
    "STORE": 2,
    "MOV": 3,
    "PUSH": 4,
    "POP": 5,
    "ADD": 6,
    "ADC": 7,
    "SUB": 8,
    "SBC": 9,
    "INC": 10,
    "DEC": 11,
    "LSH": 12,
    "RSH": 13,
    "AND": 14,
    "OR": 15,
    "NOR": 16,
    "NOT": 17,
    "XOR": 18,
    "INB": 19,
    "OUTB": 20,
    "CMP": 21,
    "JMP": 22,
    "JZ": 23,
    "JNZ": 24,
    "JC": 25,
    "JNC": 26,
    "CALL": 27,
    "RET": 28,
    "INT": 29,
    "IRET": 30,
    "NOP": 31,
}

REGISTERS = {
    # General purpose registers
    "A": 0x0, # general purpose / accumulator
    "B": 0x1,
    "C": 0x2,
    "D": 0x3,
    "E": 0x4,
    "X": 0x4,
    "Y": 0x5,
    # Memory-mapped registers
    "PC": 0x8,  # Program Counter (read-only)
    "SP": 0x9,  # Stack Pointer
    "MB": 0xA,  # Memory Bank
    "F": 0x6,  # Flags
    "Z": 0x7,  # Zero (read-only, always equal to 0x0000)
}

OPERAND_TYPES = {
    "NUMBER": 0,
    "REGISTER": 1,
    "LABELNAME": 2,
    "MACRO_ARG": 2,
    "EXPRESSION": 3,
}

OPERAND_TYPE_TO_STRING = {
    OPERAND_TYPES["LABELNAME"]: "LABELNAME",
    OPERAND_TYPES["NUMBER"]: "NUMBER",
    OPERAND_TYPES["REGISTER"]: "REGISTER",
    OPERAND_TYPES["MACRO_ARG"]: "MACRO_ARG",
    OPERAND_TYPES["EXPRESSION"]: "EXPRESSION",
}

ADDRESSING_MODES = {
    "NULL": -1, # for instructions that take no operands, addressing mode is undefined
    "REGISTER": 0,
    "IMMEDIATE": 1,
    "IMMEDIATE_ADDRESS": 2,
    "REGISTER_ADDRESS": 3,
}

ADDRESSING_MODE_TO_STRING = {
    ADDRESSING_MODES["NULL"]: "NULL",
    ADDRESSING_MODES["REGISTER"]: "REGISTER",
    ADDRESSING_MODES["IMMEDIATE"]: "IMMEDIATE",
    ADDRESSING_MODES["IMMEDIATE_ADDRESS"]: "IMMEDIATE_ADDRESS",
    ADDRESSING_MODES["REGISTER_ADDRESS"]: "REGISTER_ADDRESS",
}

ADDRESSING_MODE_TO_SIZE = {
    ADDRESSING_MODES["NULL"]: 2,
    ADDRESSING_MODES["REGISTER"]: 2,
    ADDRESSING_MODES["IMMEDIATE"]: 4,
    ADDRESSING_MODES["IMMEDIATE_ADDRESS"]: 4,
    ADDRESSING_MODES["REGISTER_ADDRESS"]: 2,
}

# list of operands, for example reg num or num or reg reg
# we need to know what kind of encoding we need to use for each operand

class LOC(Enum):
    REGA = 0
    REGB = 1
    IMM16 = 2

class OPS(Enum):
    FIRST_OPERAND = 0
    SECOND_OPERAND = 1

INSTRUCTION_ENCODINGS = {
    "HALT": {
        ADDRESSING_MODES["NULL"]: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
    },
    "LOAD": {
        ADDRESSING_MODES["REGISTER_ADDRESS"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE_ADDRESS"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    "STORE": {
        ADDRESSING_MODES["REGISTER_ADDRESS"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE_ADDRESS"]: {
            LOC.REGA: None,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: OPS.FIRST_OPERAND,
        },
    },
    "MOV": {
        ADDRESSING_MODES["REGISTER"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    "PUSH": {
        ADDRESSING_MODES["REGISTER"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE"]: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: OPS.FIRST_OPERAND,
        },
    },
    "POP": {
        ADDRESSING_MODES["REGISTER"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
    },
    "ADD": {
        ADDRESSING_MODES["REGISTER"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    "ADC": {
        ADDRESSING_MODES["REGISTER"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    "SUB": {
        ADDRESSING_MODES["REGISTER"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    "SBC": {
        ADDRESSING_MODES["REGISTER"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    "INC": {
        ADDRESSING_MODES["REGISTER"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
    },
    "DEC": {
        ADDRESSING_MODES["REGISTER"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
    },
    "LSH": {
        ADDRESSING_MODES["REGISTER"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    "RSH": {
        ADDRESSING_MODES["REGISTER"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    "AND": {
        ADDRESSING_MODES["REGISTER"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    "OR": {
        ADDRESSING_MODES["REGISTER"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    "NOR": {
        ADDRESSING_MODES["REGISTER"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
    },
    "NOT": {
        ADDRESSING_MODES["REGISTER"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
    },
    "XOR": {
        ADDRESSING_MODES["REGISTER"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    "INB": {
        ADDRESSING_MODES["REGISTER"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    "OUTB": {
        ADDRESSING_MODES["REGISTER"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE"]: {
            LOC.REGA: None,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: OPS.FIRST_OPERAND,
        },
    },
    "CMP": {
        ADDRESSING_MODES["REGISTER"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    "JMP": {
        ADDRESSING_MODES["REGISTER_ADDRESS"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE_ADDRESS"]: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: OPS.FIRST_OPERAND,
        },
    },
    "JZ": {
        ADDRESSING_MODES["REGISTER_ADDRESS"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE_ADDRESS"]: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: OPS.FIRST_OPERAND,
        },
    },
    "JNZ": {
        ADDRESSING_MODES["REGISTER_ADDRESS"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE_ADDRESS"]: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: OPS.FIRST_OPERAND,
        },
    },
    "JC": {
        ADDRESSING_MODES["REGISTER_ADDRESS"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE_ADDRESS"]: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: OPS.FIRST_OPERAND,
        },
    },
    "JNC": {
        ADDRESSING_MODES["REGISTER_ADDRESS"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE_ADDRESS"]: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: OPS.FIRST_OPERAND,
        },
    },
    "CALL": {
        ADDRESSING_MODES["REGISTER_ADDRESS"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE_ADDRESS"]: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: OPS.FIRST_OPERAND,
        },
    },
    "RET": {
        ADDRESSING_MODES["NULL"]: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
    },
    "INT": {
        ADDRESSING_MODES["REGISTER"]: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
        ADDRESSING_MODES["IMMEDIATE"]: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: OPS.FIRST_OPERAND,
        },
    },
    "IRET": {
        ADDRESSING_MODES["NULL"]: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
    },
    "NOP": {
        ADDRESSING_MODES["NULL"]: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
    },
}

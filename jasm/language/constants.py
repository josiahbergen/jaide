# language/constants.py
# language constants used by the assembler.
# josiah bergen, december 2025

OPCODES = {
    "GET": 0,
    "PUT": 1,
    "MOV": 2,
    "PUSH": 3,
    "POP": 4,
    "ADD": 5,
    "ADC": 6,
    "SUB": 7,
    "SBC": 8,
    "INC": 9,
    "DEC": 10,
    "LSH": 11,
    "RSH": 12,
    "AND": 13,
    "OR": 14,
    "NOR": 15,
    "NOT": 16,
    "XOR": 17,
    "INB": 18,
    "OUTB": 19,
    "CMP": 20,
    "JMP": 21,
    "JZ": 22,
    "JNZ": 23,
    "JC": 24,
    "JNC": 25,
    "CALL": 26,
    "RET": 27,
    "INT": 28,
    "IRET": 29,
    "HALT": 30,
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
    "NO_OPERANDS": 0,
    "REGISTER": 1,
    "IMMEDIATE": 2,
    "REGISTER_REGISTER": 3,
    "REGISTER_IMMEDIATE": 4,
}

ADDRESSING_MODE_TO_SIZE = {
    ADDRESSING_MODES["NO_OPERANDS"]: 1,
    ADDRESSING_MODES["REGISTER"]: 2,
    ADDRESSING_MODES["IMMEDIATE"]: 4,
    ADDRESSING_MODES["REGISTER_REGISTER"]: 2,
    ADDRESSING_MODES["REGISTER_IMMEDIATE"]: 4,
}

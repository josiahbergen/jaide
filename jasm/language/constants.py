# language/constants.py
# language constants used by the assembler.
# josiah bergen, december 2025

OPCODES = {
    "LOAD": 0x0,
    "STORE": 0x1,
    "MOVE": 0x2,
    "PUSH": 0x3,
    "POP": 0x4,
    "ADD": 0x5,
    "ADDC": 0x6,
    "SUB": 0x7,
    "SUBB": 0x8,
    "INC": 0x9,
    "DEC": 0xA,
    "LSH": 0xB,
    "RSH": 0xC,
    "AND": 0xD,
    "OR": 0xE,
    "NOR": 0xF,
    "NOT": 0x10,
    "XOR": 0x11,
    "INB": 0x12,
    "OUTB": 0x13,
    "CMP": 0x14,
    "SEC": 0x15,
    "CLC": 0x16,
    "CLZ": 0x17,
    "JUMP": 0x18,
    "JZ": 0x19,
    "JNZ": 0x1A,
    "JC": 0x1B,
    "JNC": 0x1C,
    "INT": 0x1D,
    "HALT": 0x1E,
    "NOP": 0x1F,
}

REGISTERS = {
    # General purpose registers
    "A": 0x0,  # General purpose / accumulator
    "B": 0x1,  # General purpose
    "C": 0x2,  # General purpose
    "D": 0x3,  # General purpose
    "X": 0x4,  # Low address / general purpose
    "Y": 0x5,  # High address / general purpose
    # Memory-mapped registers
    "F": 0x6,  # Flags
    "Z": 0x7,  # Zero
    "PC": 0x8,  # Program Counter (read-only)
    "SP": 0x9,  # Stack Pointer
    "MB": 0xA,  # Memory Bank
    "STS": 0xB,  # Status
}

OPERAND_TYPES = {
    "LABELNAME": 0,
    "NUMBER": 1,
    "REGISTER": 2,
    "REGISTER_PAIR": 3,
    "IMM8": 4,
    "IMM16": 5,
}

OPERAND_TYPE_TO_STRING = {
    OPERAND_TYPES["LABELNAME"]: "LABELNAME",
    OPERAND_TYPES["NUMBER"]: "NUMBER",
    OPERAND_TYPES["REGISTER"]: "REGISTER",
    OPERAND_TYPES["REGISTER_PAIR"]: "REGISTER_PAIR",
}

ADDRESSING_MODES = {
    "NO_OPERANDS": 0,
    "REGISTER": 1,
    "IMM8": 2,
    "REGISTER_REGISTER": 3,
    "REGISTER_IMM8": 4,
    "REGISTER_IMM16_ADDRESS": 5,
    "REGISTER_REGPAIR_ADDRESS": 6,
    "IMM16": 7,
}

ADDRESSING_MODE_TO_SIZE = {
    ADDRESSING_MODES["NO_OPERANDS"]: 1,
    ADDRESSING_MODES["REGISTER"]: 2,
    ADDRESSING_MODES["IMM8"]: 3,
    ADDRESSING_MODES["REGISTER_REGISTER"]: 2,
    ADDRESSING_MODES["REGISTER_IMM8"]: 3,
    ADDRESSING_MODES["REGISTER_IMM16_ADDRESS"]: 4,
    ADDRESSING_MODES["REGISTER_REGPAIR_ADDRESS"]: 3,
    ADDRESSING_MODES["IMM16"]: 4,
}

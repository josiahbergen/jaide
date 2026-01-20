# language/constants.py
# language constants used by the assembler.
# josiah bergen, december 2025

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
    "REGISTER": 0,
    "IMMEDIATE": 1,
    "IMMEDIATE_ADDRESS": 2,
    "REGISTER_ADDRESS": 3,
    "NULL": -1,
}

ADDRESSING_MODE_TO_SIZE = {
    ADDRESSING_MODES["NULL"]: 2,
    ADDRESSING_MODES["REGISTER"]: 2,
    ADDRESSING_MODES["IMMEDIATE"]: 4,
    ADDRESSING_MODES["IMMEDIATE_ADDRESS"]: 4,
    ADDRESSING_MODES["REGISTER_ADDRESS"]: 2,
}

ENCODING_MODES = {
    "R": 0
    "RI": 1
    "RI_R": 2
    

                match self.mnemonic:            
                # RA
                case "POP" | "INC" | "DEC" | "NOT":
                    assert_num_operands(1)
                    assert_operand_types([[OPERAND_TYPES["REGISTER"]]])

                # RA/IMM8 and [IMM16]/[RA]
                case "PUSH" | "CALL" | "INT" | "JMP" | "JZ" | "JNZ" | "JC" | "JNC":
                    assert_num_operands(1)
                    assert_operand_types([[OPERAND_TYPES["NUMBER"], OPERAND_TYPES["REGISTER"], OPERAND_TYPES["LABELNAME"]]])

                # RA/IMM16, RB and [RA]/[IMM16], RB
                case "OUTB" | "STORE":
                    assert_num_operands(2)
                    assert_operand_types([[OPERAND_TYPES["REGISTER"], OPERAND_TYPES["NUMBER"], OPERAND_TYPES["LABELNAME"]], [OPERAND_TYPES["REGISTER"]]])

                # RA, RB/IMM16 and RA, [RB]/[IMM16]
                case "MOV" | "ADD" | "ADC" | "SUB" | "SBC" | "LSH" | "RSH" | "AND" | "OR" | "NOR" | "XOR" | "INB" | "CMP" | "LOAD":
                    assert_num_operands(2)
                    assert_operand_types([[OPERAND_TYPES["REGISTER"]], [OPERAND_TYPES["REGISTER"], OPERAND_TYPES["NUMBER"], OPERAND_TYPES["LABELNAME"]]])

                case _:
                    logger.fatal(f"unknown instruction {self.mnemonic} on line {self.line}", scope)

}
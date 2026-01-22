
# constants.py
# constants used by the jaide emulator.
# josiah bergen, january 2026

from enum import Enum


MEMORY_SIZE = 0x1FFFF + 1 # 128KiB, word addressable
BANK_SIZE = 0x4000 # 32KiB, word addressable
NUM_BANKS = 31 # 32 banks total, 0 is for built-in RAM

REGISTERS = ["A", "B", "C", "D", "E", "X", "Y", "MB", "F", "Z", "SP", "PC"]

FLAG_C = 0 # carry
FLAG_Z = 1 # zero
FLAG_N = 2 # negative
FLAG_O = 3 # overflow
FLAG_I = 4 # interrupts enabled

# mnemonics
OP_HALT = 0
OP_GET = 1
OP_PUT = 2
OP_MOV = 3
OP_PUSH = 4
OP_POP = 5
OP_ADD = 6
OP_ADC = 7
OP_SUB = 8
OP_SBC = 9
OP_INC = 10
OP_DEC = 11
OP_LSH = 12
OP_RSH = 13
OP_AND = 14
OP_OR = 15
OP_NOR = 16
OP_NOT = 17
OP_XOR = 18
OP_INB = 19
OP_OUTB = 20
OP_CMP = 21
OP_JMP = 22
OP_JZ = 23
OP_JNZ = 24
OP_JC = 25
OP_JNC = 26
OP_CALL = 27
OP_RET = 28
OP_INT = 29
OP_IRET = 30
OP_NOP = 31

MNEMONICS: dict[int, str] = {
    OP_HALT: "HALT",
    OP_GET: "GET",
    OP_PUT: "PUT",
    OP_MOV: "MOV",
    OP_PUSH: "PUSH",
    OP_POP: "POP",
    OP_ADD: "ADD",
    OP_ADC: "ADC",
    OP_SUB: "SUB",
    OP_SBC: "SBC",
    OP_INC: "INC",
    OP_DEC: "DEC",
    OP_LSH: "LSH",
    OP_RSH: "RSH",
    OP_AND: "AND",
    OP_OR: "OR",
    OP_NOR: "NOR",
    OP_NOT: "NOT",
    OP_XOR: "XOR",  
    OP_INB: "INB",
    OP_OUTB: "OUTB",
    OP_CMP: "CMP",
    OP_JMP: "JMP",
    OP_JZ: "JZ",
    OP_JNZ: "JNZ",
    OP_JC: "JC",
    OP_JNC: "JNC",
    OP_CALL: "CALL",
    OP_RET: "RET",
    OP_INT: "INT",
    OP_IRET: "IRET",
    OP_NOP: "NOP",
}

# addressing modes
MODE_NULL = 0
MODE_REG = 0
MODE_IMM16 = 1
MODE_MEM_DIRECT = 2
MODE_MEM_INDIRECT = 3

MODE_TO_STRING = {
    MODE_NULL: "NULL",
    MODE_REG: "REG",
    MODE_IMM16: "IMM16",
    MODE_MEM_DIRECT: "[IMM16]",
    MODE_MEM_INDIRECT: "[REG]",
}

# addressing mode to word size
MODE_TO_SIZE = {
    MODE_NULL: 1,
    MODE_REG: 1,
    MODE_IMM16: 2,
    MODE_MEM_DIRECT: 2,
    MODE_MEM_INDIRECT: 1,
}

class LOC(Enum):
    REGA = 0
    REGB = 1
    IMM16 = 2

class OPS(Enum):
    FIRST_OPERAND = 0
    SECOND_OPERAND = 1


INSTRUCTION_ENCODINGS = {
    OP_HALT: {
        MODE_NULL: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
    },
    OP_GET: {
        MODE_MEM_INDIRECT: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        MODE_MEM_DIRECT: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    OP_PUT: {
        MODE_MEM_INDIRECT: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        MODE_MEM_DIRECT: {
            LOC.REGA: None,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: OPS.FIRST_OPERAND,
        },
    },
    OP_MOV: {
        MODE_REG: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        MODE_IMM16: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    OP_PUSH: {
        MODE_REG: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
        MODE_IMM16: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: OPS.FIRST_OPERAND,
        },
    },
    OP_POP: {
        MODE_REG: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
    },
    OP_ADD: {
        MODE_REG: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        MODE_IMM16: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    OP_ADC: {
        MODE_REG: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        MODE_IMM16: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    OP_SUB: {
        MODE_REG: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        MODE_IMM16: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    OP_SBC: {
        MODE_REG: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        MODE_IMM16: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    OP_INC: {
        MODE_REG: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
    },
    OP_DEC: {
        MODE_REG: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
    },
    OP_LSH: {
        MODE_REG: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        MODE_IMM16: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    OP_RSH: {
        MODE_REG: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        MODE_IMM16: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    OP_AND: {
        MODE_REG: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        MODE_IMM16: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    OP_OR: {
        MODE_REG: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        MODE_IMM16: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    OP_NOR: {
        MODE_REG: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
    },
    OP_NOT: {
        MODE_REG: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
    },
    OP_XOR: {
        MODE_REG: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        MODE_IMM16: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    OP_INB: {
        MODE_REG: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        MODE_IMM16: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    OP_OUTB: {
        MODE_REG: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        MODE_IMM16: {
            LOC.REGA: None,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: OPS.FIRST_OPERAND,
        },
    },
    OP_CMP: {
        MODE_REG: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: OPS.SECOND_OPERAND,
            LOC.IMM16: None,
        },
        MODE_IMM16: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: OPS.SECOND_OPERAND,
        },
    },
    OP_JMP: {
        MODE_MEM_INDIRECT: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
        MODE_MEM_DIRECT: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: OPS.FIRST_OPERAND,
        },
    },
    OP_JZ: {
        MODE_MEM_INDIRECT: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
        MODE_MEM_DIRECT: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: OPS.FIRST_OPERAND,
        },
    },
    OP_JNZ: {
        MODE_MEM_INDIRECT: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
        MODE_MEM_DIRECT: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: OPS.FIRST_OPERAND,
        },
    },
    OP_JC: {
        MODE_MEM_INDIRECT: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
        MODE_MEM_DIRECT: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: OPS.FIRST_OPERAND,
        },
    },
    OP_JNC: {
        MODE_MEM_INDIRECT: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
        MODE_MEM_DIRECT: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: OPS.FIRST_OPERAND,
        },
    },
    OP_CALL: {
        MODE_MEM_INDIRECT: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
        MODE_MEM_DIRECT: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: OPS.FIRST_OPERAND,
        },
    },
    OP_RET: {
        MODE_NULL: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
    },
    OP_INT: {
        MODE_REG: {
            LOC.REGA: OPS.FIRST_OPERAND,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
        MODE_IMM16: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: OPS.FIRST_OPERAND,
        },
    },
    OP_IRET: {
        MODE_NULL: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
    },
    OP_NOP: {
        MODE_NULL: {
            LOC.REGA: None,
            LOC.REGB: None,
            LOC.IMM16: None,
        },
    },
}



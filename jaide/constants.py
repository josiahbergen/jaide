# constants.py
# constants used by the jaide emulator.
# josiah bergen, january 2026


# mnemonics
OP_LOAD = 0x0
OP_STORE = 0x1
OP_MOVE = 0x2
OP_PUSH = 0x3
OP_POP = 0x4
OP_ADD = 0x5
OP_ADDC = 0x6
OP_SUB = 0x7
OP_SUBB = 0x8
OP_INC = 0x9
OP_DEC = 0xA
OP_SHL = 0xB
OP_SHR = 0xC
OP_AND = 0xD
OP_OR = 0xE
OP_NOR = 0xF
OP_NOT = 0x10
OP_XOR = 0x11
OP_INB = 0x12
OP_OUTB = 0x13
OP_CMP = 0x14
OP_SEC = 0x15
OP_CLC = 0x16
OP_CLZ = 0x17
OP_JUMP = 0x18
OP_JZ = 0x19
OP_JNZ = 0x1A
OP_JC = 0x1B
OP_JNC = 0x1C
OP_INT = 0x1D
OP_HALT = 0x1E
OP_NOP = 0x1F

MNEMONICS: dict[int, str] = {
    OP_LOAD: "LOAD",
    OP_STORE: "STORE",
    OP_MOVE: "MOVE",
    OP_PUSH: "PUSH",
    OP_POP: "POP",
    OP_ADD: "ADD",
    OP_ADDC: "ADDC",
    OP_SUB: "SUB",
    OP_SUBB: "SUBB",
    OP_INC: "INC",
    OP_DEC: "DEC",
    OP_SHL: "SHL",
    OP_SHR: "SHR",
    OP_AND: "AND",
    OP_OR: "OR",
    OP_NOR: "NOR",
    OP_NOT: "NOT",
    OP_XOR: "XOR",  
    OP_INB: "INB",
    OP_OUTB: "OUTB",
    OP_CMP: "CMP",
    OP_SEC: "SEC",
    OP_CLC: "CLC",
    OP_CLZ: "CLZ",
    OP_JUMP: "JUMP",
    OP_JZ: "JZ",
    OP_JNZ: "JNZ",
    OP_JC: "JC",
    OP_JNC: "JNC",
    OP_INT: "INT",
    OP_HALT: "HALT",
    OP_NOP: "NOP",
}

# addressing modes
MODE_NO_OPERANDS = 0b000
MODE_REG = 0b001
MODE_IMM8 = 0b010 
MODE_REG_REG = 0b011 
MODE_REG_IMM8 = 0b100 
MODE_REG_IMM16 = 0b101 
MODE_REG_REGPAIR = 0b110
MODE_IMM16 = 0b111

ADDRESSING_MODE_TO_SIZE = {
    MODE_NO_OPERANDS: 1,
    MODE_REG: 2,
    MODE_IMM8: 3,
    MODE_REG_REG: 2,
    MODE_REG_IMM8: 3,
    MODE_REG_IMM16: 4,
    MODE_REG_REGPAIR: 4,
    MODE_IMM16: 4,
}

ADDRESSING_MODE_TO_STRING = {
    MODE_NO_OPERANDS: "no operands",
    MODE_REG: "RG--",
    MODE_IMM8: "---- IMM8",
    MODE_REG_REG: "RGRG",
    MODE_REG_IMM8: "RG-- IMM8",
    MODE_REG_IMM16: "RG-- 16LO 16HI",
    MODE_REG_REGPAIR: "RG-- RGRG",
    MODE_IMM16: "---- 16LO IMHI",
}
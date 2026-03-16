# isa.py
# shared isa definitions for the jaide project.
# josiah bergen, march 2026


from enum import IntEnum


class INSTRUCTIONS(IntEnum):

    HALT = 0
    GET  = 1
    PUT  = 2
    MOV  = 3
    PUSH = 4
    POP  = 5
    ADD  = 6
    ADC  = 7
    SUB  = 8
    SBC  = 9
    MUL  = 10
    MOD  = 11
    INC  = 12
    DEC  = 13
    LSH  = 14
    RSH  = 15
    AND  = 16
    OR   = 17
    NOT  = 18
    XOR  = 19
    INB  = 20
    OUTB = 21
    CMP  = 22
    JMP  = 23
    JZ   = 24
    JNZ  = 25
    JC   = 26
    JNC  = 27
    JN   = 28
    JNN  = 29
    JO   = 30
    JNO  = 31
    CALL = 32
    RET  = 33
    INT  = 34
    IRET = 35
    NOP  = 36
    

class REGISTERS(IntEnum):
    A  = 0
    B  = 1
    C  = 2
    D  = 3
    E  = 4
    X  = 5
    Y  = 6
    Z  = 7
    F  = 8
    MB = 9
    SP = 10
    PC = 11


class RTYPE(IntEnum):
    SRC = 0
    DEST = 1


REGISTER_SEMANTICS: dict[INSTRUCTIONS, list[RTYPE]] = {
    INSTRUCTIONS.HALT: [],
    INSTRUCTIONS.GET:  [ RTYPE.DEST, RTYPE.SRC ],
    INSTRUCTIONS.PUT:  [ RTYPE.DEST, RTYPE.SRC ],
    INSTRUCTIONS.MOV:  [ RTYPE.DEST, RTYPE.SRC ],
    INSTRUCTIONS.PUSH: [ RTYPE.SRC ],
    INSTRUCTIONS.POP:  [ RTYPE.DEST ],
    INSTRUCTIONS.ADD:  [ RTYPE.DEST, RTYPE.SRC ],
    INSTRUCTIONS.ADC:  [ RTYPE.DEST, RTYPE.SRC ],
    INSTRUCTIONS.SUB:  [ RTYPE.DEST, RTYPE.SRC ],
    INSTRUCTIONS.SBC:  [ RTYPE.DEST, RTYPE.SRC ],
    INSTRUCTIONS.MUL:  [ RTYPE.DEST, RTYPE.SRC ],
    INSTRUCTIONS.MOD:  [ RTYPE.DEST, RTYPE.SRC ],
    INSTRUCTIONS.INC:  [ RTYPE.DEST ],
    INSTRUCTIONS.DEC:  [ RTYPE.DEST ],
    INSTRUCTIONS.LSH:  [ RTYPE.DEST, RTYPE.SRC ],
    INSTRUCTIONS.RSH:  [ RTYPE.DEST, RTYPE.SRC ],
    INSTRUCTIONS.AND:  [ RTYPE.DEST, RTYPE.SRC ],
    INSTRUCTIONS.OR:   [ RTYPE.DEST, RTYPE.SRC ],
    INSTRUCTIONS.NOT:  [ RTYPE.DEST ],
    INSTRUCTIONS.XOR:  [ RTYPE.DEST, RTYPE.SRC ],
    INSTRUCTIONS.INB:  [ RTYPE.DEST, RTYPE.SRC ],
    INSTRUCTIONS.OUTB: [ RTYPE.DEST, RTYPE.SRC ],
    INSTRUCTIONS.CMP:  [ RTYPE.DEST, RTYPE.SRC ],
    INSTRUCTIONS.JMP:  [ RTYPE.SRC ],
    INSTRUCTIONS.JZ:   [ RTYPE.SRC ],
    INSTRUCTIONS.JNZ:  [ RTYPE.SRC ],
    INSTRUCTIONS.JC:   [ RTYPE.SRC ],
    INSTRUCTIONS.JNC:  [ RTYPE.SRC ],
    INSTRUCTIONS.JN:   [ RTYPE.SRC ],
    INSTRUCTIONS.JNN:  [ RTYPE.SRC ],
    INSTRUCTIONS.JO:   [ RTYPE.SRC ],
    INSTRUCTIONS.JNO:  [ RTYPE.SRC ],
    INSTRUCTIONS.CALL: [ RTYPE.SRC ],
    INSTRUCTIONS.RET:  [ ],
    INSTRUCTIONS.INT:  [ RTYPE.SRC ],
    INSTRUCTIONS.IRET: [ ],
    INSTRUCTIONS.NOP:  [ ],
}


class MODES(IntEnum):

    NULL         = 0
    REG          = 1  # reg            register value
    IMM          = 2  # imm16          immediate value
    RELATIVE     = 3  # pc + imm16     relative value
    REG_POINTER  = 4  # [reg]          memory at register
    OFF_POINTER  = 5  # [imm16 + reg]  memory at immediate + register
    REL_POINTER  = 6  # [pc + imm16]   memory at pc + imm


INSTRUCTION_MODES: dict[INSTRUCTIONS, list[tuple[MODES, ...]]] = {

    INSTRUCTIONS.HALT: [ () ],
    INSTRUCTIONS.GET:  [ (MODES.REG, MODES.REG_POINTER), (MODES.REG, MODES.REL_POINTER), (MODES.REG, MODES.OFF_POINTER) ],
    INSTRUCTIONS.PUT:  [ (MODES.REG_POINTER, MODES.REG), (MODES.OFF_POINTER, MODES.REG) ],
    INSTRUCTIONS.MOV:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM), (MODES.REG, MODES.RELATIVE) ],
    INSTRUCTIONS.PUSH: [ (MODES.REG, ), (MODES.IMM, ) ],
    INSTRUCTIONS.POP:  [ (MODES.REG, ) ],
    INSTRUCTIONS.ADD:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.ADC:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.SUB:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.SBC:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.MUL:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.MOD:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.INC:  [ (MODES.REG, ) ],
    INSTRUCTIONS.DEC:  [ (MODES.REG, ) ],
    INSTRUCTIONS.LSH:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.RSH:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.AND:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.OR:   [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.NOT:  [ (MODES.REG, ) ],
    INSTRUCTIONS.XOR:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.INB:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.OUTB: [ (MODES.REG, MODES.REG), (MODES.IMM, MODES.REG) ],
    INSTRUCTIONS.CMP:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.JMP:  [ (MODES.REG, ), (MODES.IMM, ), (MODES.RELATIVE, ), (MODES.OFF_POINTER, ) ],
    INSTRUCTIONS.JZ:   [ (MODES.RELATIVE, ) ],
    INSTRUCTIONS.JNZ:  [ (MODES.RELATIVE, ) ],
    INSTRUCTIONS.JC:   [ (MODES.RELATIVE, ) ],
    INSTRUCTIONS.JNC:  [ (MODES.RELATIVE, ) ],
    INSTRUCTIONS.JN:   [ (MODES.RELATIVE, ) ],
    INSTRUCTIONS.JNN:  [ (MODES.RELATIVE, ) ],
    INSTRUCTIONS.JO:   [ (MODES.RELATIVE, ) ],
    INSTRUCTIONS.JNO:  [ (MODES.RELATIVE, ) ],
    INSTRUCTIONS.CALL: [ (MODES.REG, ), (MODES.RELATIVE, ), (MODES.OFF_POINTER, )],
    INSTRUCTIONS.RET:  [ () ],
    INSTRUCTIONS.INT:  [ (MODES.REG, ), (MODES.IMM, ) ],
    INSTRUCTIONS.IRET: [ () ],
    INSTRUCTIONS.NOP:  [ () ],
}


OPCODE_MAP_KEYS: list[tuple[INSTRUCTIONS, tuple[MODES, ...]]] = [
    (instr, modes)
    for instr, mode_list in INSTRUCTION_MODES.items()
    for modes in mode_list
]


OPCODE_MAP: dict[tuple[INSTRUCTIONS, tuple[MODES, ...]], int] = {
    (instr, modes): i
    for i, (instr, modes) in enumerate[tuple[INSTRUCTIONS, tuple[MODES, ...]]](OPCODE_MAP_KEYS)
}


def generate_opcode_string(opcode: int) -> str | None:
    """ Generate a string representation of the opcode and operands. """

    mode_string: dict[MODES, str] = {
        MODES.REG: "reg",
        MODES.IMM: "imm16",
        MODES.REG_POINTER: "[reg]",
        MODES.REL_POINTER: "[pc + imm16]",
        MODES.OFF_POINTER: "[imm16 + reg]",
    }

    mnemonic = None
    operands = None

    # reverse lookup on the mappings to get the mnemonic and operands
    for (mnemonic, operands), code in OPCODE_MAP.items():
        if code == opcode:
            mnemonic = mnemonic
            operands = operands
            break

    if operands is None or mnemonic is None:
        # no matching opcode
        return None

    return f"{mnemonic.name} {', '.join([mode_string[mode] for mode in operands])}".strip()


if __name__ == "__main__":

    for mnemonic in INSTRUCTIONS:
        print(f"{mnemonic.name}:")
        all_encodings = [encoding for encoding in OPCODE_MAP.keys() if encoding[0] == mnemonic]
        for encoding in all_encodings:
            print(f"    {generate_opcode_string(OPCODE_MAP[encoding])}")
        print()

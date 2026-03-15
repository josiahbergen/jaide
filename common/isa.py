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
    INC  = 10
    DEC  = 11
    LSH  = 12
    RSH  = 13
    AND  = 14
    OR   = 15
    NOT  = 16
    XOR  = 17
    INB  = 18
    OUTB = 19
    CMP  = 20
    JMP  = 21
    JZ   = 22
    JNZ  = 23
    JC   = 24
    JNC  = 25
    JN   = 26
    JNN  = 27
    JO   = 28
    JNO  = 29
    CALL = 30
    RET  = 31
    INT  = 32
    IRET = 33
    NOP  = 34


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


class MODES(IntEnum):

    REG          = 0  # reg            register
    IMM          = 1  # imm16          immediate value in instruction word
    REG_INDIRECT = 2  # [reg]          memory location contained in register
    REL_ADDRESS  = 3  # [imm16 + pc]   memory location defined by pc + immediate
    OFF_ADDRESS  = 4  # [imm16 + reg]  memory location defined by immediate + register


OPCODE_MAPPINGS: dict[tuple[INSTRUCTIONS, tuple[MODES, ...]], int] = {
    # turns "assembly-style" instruction information into an opcode value

    (INSTRUCTIONS.HALT, ()):                                 0x00,
    (INSTRUCTIONS.GET,  ( MODES.REG, MODES.REG_INDIRECT )):  0x01,
    (INSTRUCTIONS.GET,  ( MODES.REG, MODES.REL_ADDRESS  )):  0x02,
    (INSTRUCTIONS.GET,  ( MODES.REG, MODES.OFF_ADDRESS  )):  0x03,
    (INSTRUCTIONS.PUT,  ( MODES.REG_INDIRECT, MODES.REG )):  0x04,
    (INSTRUCTIONS.PUT,  ( MODES.OFF_ADDRESS,  MODES.REG )):  0x05,
    (INSTRUCTIONS.MOV,  ( MODES.REG, MODES.REG )):           0x06,
    (INSTRUCTIONS.MOV,  ( MODES.REG, MODES.IMM )):           0x07,
    (INSTRUCTIONS.PUSH, ( MODES.REG, )):                     0x08,
    (INSTRUCTIONS.PUSH, ( MODES.IMM, )):                     0x09,
    (INSTRUCTIONS.POP,  ( MODES.REG, )):                     0x0a,
    (INSTRUCTIONS.ADD,  ( MODES.REG, MODES.REG )):           0x0b,
    (INSTRUCTIONS.ADD,  ( MODES.REG, MODES.IMM )):           0x0c,
    (INSTRUCTIONS.ADC,  ( MODES.REG, MODES.REG )):           0x0d,
    (INSTRUCTIONS.ADC,  ( MODES.REG, MODES.IMM )):           0x0e,
    (INSTRUCTIONS.SUB,  ( MODES.REG, MODES.REG )):           0x0f,
    (INSTRUCTIONS.SUB,  ( MODES.REG, MODES.IMM )):           0x10,
    (INSTRUCTIONS.SBC,  ( MODES.REG, MODES.REG )):           0x11,
    (INSTRUCTIONS.SBC,  ( MODES.REG, MODES.IMM )):           0x12,
    (INSTRUCTIONS.INC,  ( MODES.REG, )):                     0x13,
    (INSTRUCTIONS.DEC,  ( MODES.REG, )):                     0x14,
    (INSTRUCTIONS.LSH,  ( MODES.REG, MODES.REG )):           0x15,
    (INSTRUCTIONS.LSH,  ( MODES.REG, MODES.IMM )):           0x16,
    (INSTRUCTIONS.RSH,  ( MODES.REG, MODES.REG )):           0x17,
    (INSTRUCTIONS.RSH,  ( MODES.REG, MODES.IMM )):           0x18,
    (INSTRUCTIONS.AND,  ( MODES.REG, MODES.REG )):           0x19,
    (INSTRUCTIONS.AND,  ( MODES.REG, MODES.IMM )):           0x1a,
    (INSTRUCTIONS.OR,   ( MODES.REG, MODES.REG )):           0x1b,
    (INSTRUCTIONS.OR,   ( MODES.REG, MODES.IMM )):           0x1c,
    (INSTRUCTIONS.NOT,  ( MODES.REG, )):                     0x1d,
    (INSTRUCTIONS.XOR,  ( MODES.REG, MODES.REG )):           0x1e,
    (INSTRUCTIONS.XOR,  ( MODES.REG, MODES.IMM )):           0x1f,
    (INSTRUCTIONS.INB,  ( MODES.REG, MODES.REG )):           0x20,
    (INSTRUCTIONS.INB,  ( MODES.REG, MODES.IMM )):           0x21,
    (INSTRUCTIONS.OUTB, ( MODES.REG, MODES.REG )):           0x22,
    (INSTRUCTIONS.OUTB, ( MODES.REG, MODES.IMM )):           0x23,
    (INSTRUCTIONS.CMP,  ( MODES.REG, MODES.REG )):           0x24,
    (INSTRUCTIONS.CMP,  ( MODES.REG, MODES.IMM )):           0x25,
    (INSTRUCTIONS.JMP,  ( MODES.REG, )):                     0x26,
    (INSTRUCTIONS.JMP,  ( MODES.IMM, )):                     0x27,
    (INSTRUCTIONS.JMP,  ( MODES.REL_ADDRESS, )):             0x28,
    (INSTRUCTIONS.JMP,  ( MODES.OFF_ADDRESS, )):             0x29,
    (INSTRUCTIONS.JZ,   ( MODES.REL_ADDRESS, )):             0x2a,
    (INSTRUCTIONS.JNZ,  ( MODES.REL_ADDRESS, )):             0x2b,
    (INSTRUCTIONS.JC,   ( MODES.REL_ADDRESS, )):             0x2c,
    (INSTRUCTIONS.JNC,  ( MODES.REL_ADDRESS, )):             0x2d,
    (INSTRUCTIONS.JN,   ( MODES.REL_ADDRESS, )):             0x2e,
    (INSTRUCTIONS.JNN,  ( MODES.REL_ADDRESS, )):             0x2f,
    (INSTRUCTIONS.JO,   ( MODES.REL_ADDRESS, )):             0x30,
    (INSTRUCTIONS.JNO,  ( MODES.REL_ADDRESS, )):             0x31,
    (INSTRUCTIONS.CALL, ( MODES.REG, )):                     0x32,
    (INSTRUCTIONS.CALL, ( MODES.IMM, )):                     0x33,
    (INSTRUCTIONS.RET,  ()):                                 0x34,
    (INSTRUCTIONS.INT,  ( MODES.REG, )):                     0x35,
    (INSTRUCTIONS.INT,  ( MODES.IMM, )):                     0x36,
    (INSTRUCTIONS.IRET, ()):                                 0x37,
    (INSTRUCTIONS.NOP,  ()):                                 0x38,
}


def generate_opcode_string(opcode: int) -> str | None:
    """ Generate a string representation of the opcode and operands. """

    mode_string: dict[MODES, str] = {
        MODES.REG: "reg",
        MODES.IMM: "imm16",
        MODES.REG_INDIRECT: "[reg]",
        MODES.REL_ADDRESS: "[pc + imm16]",
        MODES.OFF_ADDRESS: "[imm16 + reg]",
    }

    mnemonic = None
    operands = None

    # reverse lookup on the mappings to get the mnemonic and operands
    for (mnemonic, operands), code in OPCODE_MAPPINGS.items():
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
        all_encodings = [encoding for encoding in OPCODE_MAPPINGS.keys() if encoding[0] == mnemonic]
        for encoding in all_encodings:
            print(f"    {generate_opcode_string(OPCODE_MAPPINGS[encoding])}")
        print()

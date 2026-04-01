# isa.py
# shared isa definitions for the jaide project.
# josiah bergen, march 2026

from tap import Tap
from dataclasses import dataclass
from enum import IntEnum, auto

class INSTRUCTIONS(IntEnum):
    """all supported instructions"""

    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return count # ensure 0-indexing

    NOP  = auto()
    HALT = auto()
    GET  = auto()
    PUT  = auto()
    MOV  = auto()
    PUSH = auto()
    POP  = auto()
    ADD  = auto()
    ADC  = auto()
    SUB  = auto()
    SBC  = auto()
    MUL  = auto()
    MOD  = auto()
    DIV  = auto()
    INC  = auto()
    DEC  = auto()
    LSH  = auto()
    RSH  = auto()
    ASR  = auto()
    AND  = auto()
    OR   = auto()
    NOT  = auto()
    XOR  = auto()
    SWP  = auto()
    INB  = auto()
    OUTB = auto()
    CMP  = auto()
    JMP  = auto()
    JZ   = auto()
    JNZ  = auto()
    JC   = auto()
    JNC  = auto()
    JA   = auto()
    JAE  = auto()
    JB   = auto()
    JBE  = auto()
    JG   = auto()
    JGE  = auto()
    JL   = auto()
    JLE  = auto()
    CALL = auto()
    RET  = auto()
    INT  = auto()
    IRET = auto()


class REGISTERS(IntEnum):
    """all the registers"""

    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return count # ensure 0-indexing

    A  = auto()
    B  = auto()
    C  = auto()
    D  = auto()
    E  = auto()
    X  = auto()
    Y  = auto()
    Z  = auto()
    F  = auto()
    MB = auto()
    SP = auto()
    PC = auto()


class MODES(IntEnum):
    """addressing modes for instructions"""

                          # syntax       parsed         where does the value come from?
    REG         = auto()  # a            reg            register value
    IMM         = auto()  # 0x0000       imm16          immediate value
    RELATIVE    = auto()  # label        imm16          immediate value
    REG_POINTER = auto()  # [a]          [reg]          memory at register
    OFF_POINTER = auto()  # [label + a]  [imm16 + reg]  memory at immediate + register
    REL_POINTER = auto()  # [label]      [pc + imm16]   memory at pc + imm16

    NULL        = auto()  # placeholder, used during parsing


INSTRUCTION_MODES: dict[INSTRUCTIONS, list[tuple[MODES, ...]]] = {

    INSTRUCTIONS.HALT: [ () ],
    INSTRUCTIONS.GET:  [ (MODES.REG, MODES.REG_POINTER), ],
    # PIC: (MODES.REG, MODES.REL_POINTER), (MODES.REG, MODES.OFF_POINTER)
 
    INSTRUCTIONS.PUT:  [ (MODES.REG_POINTER, MODES.REG), (MODES.REG_POINTER, MODES.IMM)],
    # PIC: (MODES.OFF_POINTER, MODES.REG), (MODES.REL_POINTER, MODES.REG)

    INSTRUCTIONS.MOV:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM)],
    # PIC: (MODES.REG, MODES.RELATIVE)

    INSTRUCTIONS.PUSH: [ (MODES.REG, ), (MODES.IMM, ) ],
    INSTRUCTIONS.POP:  [ (MODES.REG, ) ],
    INSTRUCTIONS.ADD:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.ADC:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.SUB:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.SBC:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.MUL:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.DIV:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.MOD:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.INC:  [ (MODES.REG, ) ],
    INSTRUCTIONS.DEC:  [ (MODES.REG, ) ],
    INSTRUCTIONS.LSH:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.RSH:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.ASR:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.AND:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.OR:   [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.NOT:  [ (MODES.REG, ) ],
    INSTRUCTIONS.XOR:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.SWP:  [ (MODES.REG, MODES.REG) ],
    INSTRUCTIONS.INB:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.OUTB: [ (MODES.REG, MODES.REG), (MODES.IMM, MODES.REG) ],
    INSTRUCTIONS.CMP:  [ (MODES.REG, MODES.REG), (MODES.REG, MODES.IMM) ],
    INSTRUCTIONS.JMP:  [ (MODES.REG, ), (MODES.IMM, ) ],
    # PIC: (MODES.RELATIVE,), (MODES.OFF_POINTER)

    INSTRUCTIONS.JZ:   [ (MODES.RELATIVE, ) ],
    INSTRUCTIONS.JNZ:  [ (MODES.RELATIVE, ) ],
    INSTRUCTIONS.JC:   [ (MODES.RELATIVE, ) ],
    INSTRUCTIONS.JNC:  [ (MODES.RELATIVE, ) ],
    INSTRUCTIONS.JA:   [ (MODES.RELATIVE, ) ],
    INSTRUCTIONS.JAE:  [ (MODES.RELATIVE, ) ],
    INSTRUCTIONS.JB:   [ (MODES.RELATIVE, ) ],
    INSTRUCTIONS.JBE:  [ (MODES.RELATIVE, ) ],
    INSTRUCTIONS.JG:   [ (MODES.RELATIVE, ) ],
    INSTRUCTIONS.JGE:  [ (MODES.RELATIVE, ) ],
    INSTRUCTIONS.JL:   [ (MODES.RELATIVE, ) ],
    INSTRUCTIONS.JLE:  [ (MODES.RELATIVE, ) ],
    INSTRUCTIONS.CALL: [ (MODES.REG, ), (MODES.IMM, ) ],
    # PIC: (MODES.RELATIVE,), (MODES.OFF_POINTER)

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


@dataclass(frozen=True)
class InstructionFormat:
    mnemonic:     INSTRUCTIONS
    modes:        tuple[MODES, ...] # modes of the operands that this opcode uses, looks like (MODES.REG, MODES.IMM)
    src_operand:  int | None        # operand index of ssss
    dest_operand: int | None        # operand index of dddd
    imm_operand:  int | None        # operand index of immediate word


# (mnemonic, modes) → (src_operand, dest_operand, imm_operand)
_FORMAT_DATA: dict[tuple[INSTRUCTIONS, tuple[MODES, ...]], tuple[int | None, int | None, int | None]] = {

    (INSTRUCTIONS.HALT, ()):                                (None, None, None),

    # GET dest, src
    # reg: ssss=src ptr reg  dddd=dest reg                 src    dest  imm
    (INSTRUCTIONS.GET, (MODES.REG, MODES.REG_POINTER)):    (1,    0,    None),
    # (INSTRUCTIONS.GET, (MODES.REG, MODES.REL_POINTER)):  (None, 0,    1   ),
    # (INSTRUCTIONS.GET, (MODES.REG, MODES.OFF_POINTER)):  (1,    0,    1   ),

    # PUT dest, src
    # reg: ssss=src reg  dddd=dest ptr reg
    (INSTRUCTIONS.PUT, (MODES.REG_POINTER, MODES.REG)):    (1,    0,    None),
    # imm: dddd=dest ptr reg  imm=value to store
    (INSTRUCTIONS.PUT, (MODES.REG_POINTER, MODES.IMM)):    (None, 0,    1   ),
    # (INSTRUCTIONS.PUT, (MODES.OFF_POINTER, MODES.REG)):  (1,    0,    0   ),
    # (INSTRUCTIONS.PUT, (MODES.REL_POINTER, MODES.REG)):  (1,    None, 0   ),

    # MOV dest, src
    # reg+reg: ssss=src  dddd=dest
    # reg+imm: ssss=dest (anomaly: dest register goes in source slot when src is an immediate)
    (INSTRUCTIONS.MOV, (MODES.REG, MODES.REG)):            (1,    0,    None),
    (INSTRUCTIONS.MOV, (MODES.REG, MODES.IMM)):            (0,    None, 1   ),
    # (INSTRUCTIONS.MOV, (MODES.REG, MODES.RELATIVE)):     (0,    None, 1   ),

    # PUSH src
    (INSTRUCTIONS.PUSH, (MODES.REG,)):                     (0,    None, None),
    (INSTRUCTIONS.PUSH, (MODES.IMM,)):                     (None, None, 0   ),

    # POP dest
    (INSTRUCTIONS.POP, (MODES.REG,)):                      (None, 0,    None),

    # ALU binary ops: ssss=src(op1)  dddd=dest(op0)
    (INSTRUCTIONS.ADD, (MODES.REG, MODES.REG)):            (1,    0,    None),
    (INSTRUCTIONS.ADD, (MODES.REG, MODES.IMM)):            (None, 0,    1   ),

    (INSTRUCTIONS.ADC, (MODES.REG, MODES.REG)):            (1,    0,    None),
    (INSTRUCTIONS.ADC, (MODES.REG, MODES.IMM)):            (None, 0,    1   ),

    (INSTRUCTIONS.SUB, (MODES.REG, MODES.REG)):            (1,    0,    None),
    (INSTRUCTIONS.SUB, (MODES.REG, MODES.IMM)):            (None, 0,    1   ),

    (INSTRUCTIONS.SBC, (MODES.REG, MODES.REG)):            (1,    0,    None),
    (INSTRUCTIONS.SBC, (MODES.REG, MODES.IMM)):            (None, 0,    1   ),

    (INSTRUCTIONS.MUL, (MODES.REG, MODES.REG)):            (1,    0,    None),
    (INSTRUCTIONS.MUL, (MODES.REG, MODES.IMM)):            (None, 0,    1   ),

    (INSTRUCTIONS.MOD, (MODES.REG, MODES.REG)):            (1,    0,    None),
    (INSTRUCTIONS.MOD, (MODES.REG, MODES.IMM)):            (None, 0,    1   ),

    (INSTRUCTIONS.DIV, (MODES.REG, MODES.REG)):            (1,    0,    None),
    (INSTRUCTIONS.DIV, (MODES.REG, MODES.IMM)):            (None, 0,    1   ),

    # ALU unary ops: dddd=dest
    (INSTRUCTIONS.INC, (MODES.REG,)):                      (None, 0,    None),
    (INSTRUCTIONS.DEC, (MODES.REG,)):                      (None, 0,    None),
    (INSTRUCTIONS.NOT, (MODES.REG,)):                      (None, 0,    None),

    (INSTRUCTIONS.LSH, (MODES.REG, MODES.REG)):            (1,    0,    None),
    (INSTRUCTIONS.LSH, (MODES.REG, MODES.IMM)):            (None, 0,    1   ),

    (INSTRUCTIONS.RSH, (MODES.REG, MODES.REG)):            (1,    0,    None),
    (INSTRUCTIONS.RSH, (MODES.REG, MODES.IMM)):            (None, 0,    1   ),

    (INSTRUCTIONS.ASR, (MODES.REG, MODES.REG)):            (1,    0,    None),
    (INSTRUCTIONS.ASR, (MODES.REG, MODES.IMM)):            (None, 0,    1   ),

    (INSTRUCTIONS.AND, (MODES.REG, MODES.REG)):            (1,    0,    None),
    (INSTRUCTIONS.AND, (MODES.REG, MODES.IMM)):            (None, 0,    1   ),

    (INSTRUCTIONS.OR,  (MODES.REG, MODES.REG)):            (1,    0,    None),
    (INSTRUCTIONS.OR,  (MODES.REG, MODES.IMM)):            (None, 0,    1   ),

    (INSTRUCTIONS.XOR, (MODES.REG, MODES.REG)):            (1,    0,    None),
    (INSTRUCTIONS.XOR, (MODES.REG, MODES.IMM)):            (None, 0,    1   ),

    # I/O
    # INB dest, port_src: ssss=port_reg(op1)  dddd=dest(op0)
    (INSTRUCTIONS.INB, (MODES.REG, MODES.REG)):            (1,    0,    None),
    (INSTRUCTIONS.INB, (MODES.REG, MODES.IMM)):            (None, 0,    1   ),

    # OUTB port_dest, src: ssss=src(op1)  dddd=port_reg(op0)
    # OUTB imm, src:       ssss=src(op1)  imm=port_num(op0)
    (INSTRUCTIONS.OUTB, (MODES.REG, MODES.REG)):           (1,    0,    None),
    (INSTRUCTIONS.OUTB, (MODES.IMM, MODES.REG)):           (1,    None, 0   ),

    # CMP dest, src: ssss=src(op1)  dddd=dest(op0)
    # CMP dest, imm: ssss=dest(op0) (same anomaly as MOV)
    (INSTRUCTIONS.CMP, (MODES.REG, MODES.REG)):            (1,    0,    None),
    (INSTRUCTIONS.CMP, (MODES.REG, MODES.IMM)):            (0,    None, 1   ),

    # JMP
    (INSTRUCTIONS.JMP, (MODES.REG,)):                      (0,    None, None),
    (INSTRUCTIONS.JMP, (MODES.IMM,)):                      (None, None, 0   ),
    # (INSTRUCTIONS.JMP, (MODES.RELATIVE,)):               (None, None, 0   ),
    # (INSTRUCTIONS.JMP, (MODES.OFF_POINTER,)):            (0,    None, 0   ),

    # Conditional jumps (all RELATIVE)
    (INSTRUCTIONS.JZ,  (MODES.RELATIVE,)):                 (None, None, 0   ),
    (INSTRUCTIONS.JNZ, (MODES.RELATIVE,)):                 (None, None, 0   ),
    (INSTRUCTIONS.JC,  (MODES.RELATIVE,)):                 (None, None, 0   ),
    (INSTRUCTIONS.JNC, (MODES.RELATIVE,)):                 (None, None, 0   ),
    (INSTRUCTIONS.JA,  (MODES.RELATIVE,)):                 (None, None, 0   ),
    (INSTRUCTIONS.JAE, (MODES.RELATIVE,)):                 (None, None, 0   ),
    (INSTRUCTIONS.JB,  (MODES.RELATIVE,)):                 (None, None, 0   ),
    (INSTRUCTIONS.JBE, (MODES.RELATIVE,)):                 (None, None, 0   ),
    (INSTRUCTIONS.JG,  (MODES.RELATIVE,)):                 (None, None, 0   ),
    (INSTRUCTIONS.JGE, (MODES.RELATIVE,)):                 (None, None, 0   ),
    (INSTRUCTIONS.JL,  (MODES.RELATIVE,)):                 (None, None, 0   ),
    (INSTRUCTIONS.JLE, (MODES.RELATIVE,)):                 (None, None, 0   ),

    # CALL
    (INSTRUCTIONS.CALL, (MODES.REG,)):                     (0,    None, None),
    (INSTRUCTIONS.CALL, (MODES.IMM,)):                     (None, None, 0   ),
    # (INSTRUCTIONS.CALL, (MODES.RELATIVE,)):              (None, None, 0   ),
    # (INSTRUCTIONS.CALL, (MODES.OFF_POINTER,)):           (0,    None, 0   ),

    (INSTRUCTIONS.RET,  ()):                               (None, None, None),

    # INT
    (INSTRUCTIONS.INT, (MODES.REG,)):                      (0,    None, None),
    (INSTRUCTIONS.INT, (MODES.IMM,)):                      (None, None, 0   ),

    (INSTRUCTIONS.IRET, ()):                               (None, None, None),
    (INSTRUCTIONS.NOP,  ()):                               (None, None, None),

    # SWP: ssss=op0, dddd=op1
    (INSTRUCTIONS.SWP, (MODES.REG, MODES.REG)):           (0,    1,    None),
}


OPCODE_FORMATS: dict[int, InstructionFormat] = {
    opcode: InstructionFormat(
        mnemonic       = instr,
        modes          = modes,
        src_operand    = _FORMAT_DATA[(instr, modes)][0], # will be 0, 1, or None
        dest_operand   = _FORMAT_DATA[(instr, modes)][1], # will be 0, 1, or None
        imm_operand    = _FORMAT_DATA[(instr, modes)][2], # will be 0, 1, or None
    )
    for (instr, modes), opcode in OPCODE_MAP.items()
}


def generate_opcode_string(opcode: int) -> str | None:
    """ Generate a string representation of the opcode and operands. """

    mode_string: dict[MODES, str] = {
        MODES.REG:         "reg",
        MODES.IMM:         "imm",
        MODES.RELATIVE:    "imm",
        MODES.REG_POINTER: "[reg]",
        MODES.OFF_POINTER: "[imm + reg]",
        MODES.REL_POINTER: "[pc + simm]",
    }

    fmt = OPCODE_FORMATS.get(opcode)
    if fmt is None:
        return None

    operand_str = ", ".join(mode_string[m] for m in fmt.modes)
    return f"{fmt.mnemonic.name} {operand_str}".strip()


def generate_opcode_encoding_string(opcode: int) -> str:
    """ 
    Generate a string representation of the instruction encoding for the given opcode.

    String representation format is:

    mnemonic [operand] [operand] oooooooo ssss dddd xxxxxxxx xxxxxxxx 
    """

    mode_syntax_string_map: dict[MODES, str] = {
        MODES.REG:         "a",
        MODES.IMM:         "0xff",
        MODES.RELATIVE:    "label",
        MODES.REG_POINTER: "[a]",
        MODES.OFF_POINTER: "[label + a]",
        MODES.REL_POINTER: "[label]",
    }

    mode_name_map: dict[MODES, str] = {
        MODES.REG:         "reg",
        MODES.IMM:         "imm",
        MODES.RELATIVE:    "imm",
        MODES.REG_POINTER: "[reg]",
        MODES.OFF_POINTER: "[imm + reg]",
        MODES.REL_POINTER: "[imm]",
    }

    fmt = OPCODE_FORMATS.get(opcode)
    if not fmt:
        return f"no opcode found for {opcode:#04x}"

    mnemonic: str = fmt.mnemonic.name.lower()
    operand_1_mode = mode_name_map[fmt.modes[0]] if len(fmt.modes) > 0 else ""
    operand_2_mode = mode_name_map[fmt.modes[1]] if len(fmt.modes) > 1 else ""

    operand_1_syntax: str = mode_syntax_string_map[fmt.modes[0]] if len(fmt.modes) > 0 else ""
    operand_2_syntax: str = mode_syntax_string_map[fmt.modes[1]] if len(fmt.modes) > 1 else ""
    full_syntax: str = f"{mnemonic} {operand_1_syntax}{', ' if operand_1_syntax and operand_2_syntax else ''}{operand_2_syntax}"

    # this is checking "is the source register used?"
    opcode_binary: str = f"oooooooo"
    source_reg_binary: str = "ssss" if fmt.src_operand is not None else "----"
    dest_reg_binary: str = "dddd" if fmt.dest_operand is not None else "----"
    immediate_binary: str = "xxxxxxxxxxxxxxxx" if fmt.imm_operand is not None else ""

    return (
        f"{full_syntax:<14}   "
        + f"{operand_1_mode:<7}{operand_2_mode:<7}   "
        + f"{opcode_binary} {source_reg_binary} {dest_reg_binary} {immediate_binary}"
    )


class InstructionArguments(Tap):
    """argparser for generating spec docs"""

    opcode_map: bool = False
    full_spec: bool = False


if __name__ == "__main__":

    args = InstructionArguments(underscores_to_dashes=True).parse_args()

    if args.full_spec:
        print("JASM SPECIFICATION\nVERSION 0.5\n")
        print(f"instruction      src    dest      word 1            word 2")
        print(f"-------------    -----  -----     ----------------- -----------------\n")


    for mnemonic in INSTRUCTIONS:
        for (instr, modes), opcode in OPCODE_MAP.items():

            if instr == mnemonic and args.opcode_map:
                print(f"{opcode:#04x}\t{generate_opcode_string(opcode)}")

            if instr == mnemonic and args.full_spec:
                print(f"{generate_opcode_encoding_string(opcode)}")

        print()
    print(f"generated data for {len(INSTRUCTIONS)} instructions.")

    if not args.opcode_map and not args.full_spec:
        print("no arguments provided.")

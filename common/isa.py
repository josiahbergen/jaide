# isa.py
# the jaide instruction set: the single definition shared by the assembler and the emulator.
# josiah bergen, march 2026

from dataclasses import dataclass
from enum import Enum, IntEnum, auto
from typing import Sequence


class ZeroIndexedEnum(IntEnum):
    """regular int enum is 1-indexed. ugh."""

    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return count # ensure 0-indexing


class REGISTERS(ZeroIndexedEnum):
    """all the registers, in encoding order"""

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


class Mode(Enum):
    """addressing mode of a single operand"""

    REG = "reg"    # a         the value of a register
    IMM = "imm"    # 0x1234    the word following the instruction (numbers, constants, and labels)
    PTR = "[reg]"  # [a]       the memory word a register points to


REG, IMM, PTR = Mode.REG, Mode.IMM, Mode.PTR


@dataclass(frozen=True, slots=True)
class Op:
    """
    One opcode: a mnemonic specialized to the addressing mode of each operand.

    Every instruction is one 16-bit word, optionally followed by an immediate word:

        oooooooo bbbb aaaa   [iiiiiiii iiiiiiii]

    oooooooo is the opcode. bit 0 of the opcode is set exactly when an immediate word follows.
    aaaa and bbbb are the registers of the first and second REG/PTR operands, in operand order.
    """

    opcode: int
    mnemonic: str
    modes: tuple[Mode, ...] = ()

    @property
    def has_imm(self) -> bool:
        return IMM in self.modes

    @property
    def size(self) -> int:
        """size in words"""
        return 2 if self.has_imm else 1

    @property
    def signature(self) -> str:
        """looks like 'mov reg, imm'"""
        return f"{self.mnemonic} {', '.join(mode.value for mode in self.modes)}".strip()

    def encode(self, operands: Sequence[int]) -> list[int]:
        """Encode operand values (register numbers and immediates, in operand order) into words."""
        registers = [value for mode, value in zip(self.modes, operands, strict=True) if mode is not IMM]
        immediates = [value for mode, value in zip(self.modes, operands, strict=True) if mode is IMM]
        word = self.opcode << 8 | sum(register << (4 * field) for field, register in enumerate(registers))
        return [word, *immediates]

    def format(self, a: int, b: int, imm: int) -> str:
        """Render decoded fields back into jasm syntax, e.g. 'put [x], 0x0005'."""
        fields = iter((a, b))
        operands: list[str] = []
        for mode in self.modes:
            if mode is IMM:
                operands.append(f"0x{imm:04x}")
                continue
            field = next(fields)
            name = REGISTERS(field).name.lower() if field < len(REGISTERS) else f"r{field}?"
            operands.append(name if mode is REG else f"[{name}]")
        return f"{self.mnemonic} {', '.join(operands)}".strip()


# the instruction set. one row per opcode: (opcode, mnemonic, *operand modes).
# opcodes are grouped by category in the high nibble. odd opcodes take an immediate word.
_SPEC: list[tuple] = [

    # 0x0_: system
    (0x00, "halt"),  # zeroed memory halts, which catches runaway execution
    (0x02, "nop"),
    (0x04, "wait"),
    (0x06, "syscall"),
    (0x08, "transfer"),
    (0x0A, "stc"),
    (0x0C, "clc"),

    # 0x1_: registers and the stack
    (0x10, "mov",  REG, REG),
    (0x11, "mov",  REG, IMM),
    (0x12, "swp",  REG, REG),
    (0x14, "push", REG),
    (0x15, "push", IMM),
    (0x16, "pop",  REG),

    # 0x2_: memory
    (0x20, "get",  REG, PTR),
    (0x22, "put",  PTR, REG),
    (0x23, "put",  PTR, IMM),
    (0x25, "bcp",  REG, REG, IMM),

    # 0x3_, 0x4_: arithmetic
    (0x30, "add",  REG, REG),
    (0x31, "add",  REG, IMM),
    (0x32, "adc",  REG, REG),
    (0x33, "adc",  REG, IMM),
    (0x34, "sub",  REG, REG),
    (0x35, "sub",  REG, IMM),
    (0x36, "sbc",  REG, REG),
    (0x37, "sbc",  REG, IMM),
    (0x38, "mul",  REG, REG),
    (0x39, "mul",  REG, IMM),
    (0x3A, "div",  REG, REG),
    (0x3B, "div",  REG, IMM),
    (0x3C, "mod",  REG, REG),
    (0x3D, "mod",  REG, IMM),
    (0x40, "inc",  REG),
    (0x42, "dec",  REG),
    (0x44, "cmp",  REG, REG),
    (0x45, "cmp",  REG, IMM),

    # 0x5_: logic and shifts
    (0x50, "and",  REG, REG),
    (0x51, "and",  REG, IMM),
    (0x52, "or",   REG, REG),
    (0x53, "or",   REG, IMM),
    (0x54, "xor",  REG, REG),
    (0x55, "xor",  REG, IMM),
    (0x56, "not",  REG),
    (0x58, "lsh",  REG, REG),
    (0x59, "lsh",  REG, IMM),
    (0x5A, "rsh",  REG, REG),
    (0x5B, "rsh",  REG, IMM),
    (0x5C, "asr",  REG, REG),
    (0x5D, "asr",  REG, IMM),

    # 0x6_: jumps and calls
    (0x60, "jmp",  REG),
    (0x61, "jmp",  IMM),
    (0x62, "call", REG),
    (0x63, "call", IMM),
    (0x64, "ret"),

    # 0x7_, 0x8_: conditional branches
    (0x71, "jz",   IMM),
    (0x73, "jnz",  IMM),
    (0x75, "jc",   IMM),
    (0x77, "jnc",  IMM),
    (0x79, "ja",   IMM),
    (0x7B, "jae",  IMM),
    (0x7D, "jb",   IMM),
    (0x7F, "jbe",  IMM),
    (0x81, "jg",   IMM),
    (0x83, "jge",  IMM),
    (0x85, "jl",   IMM),
    (0x87, "jle",  IMM),
]

ISA: tuple[Op, ...] = tuple(Op(opcode, mnemonic, tuple(modes)) for opcode, mnemonic, *modes in _SPEC)

# lookups derived from the spec
BY_OPCODE: list[Op | None] = [None] * 256                                           # used to decode
BY_SIGNATURE: dict[tuple[str, tuple[Mode, ...]], Op] = {}                           # used to encode
MNEMONICS: tuple[str, ...] = tuple(dict.fromkeys(op.mnemonic for op in ISA))        # in spec order

for _op in ISA:
    assert BY_OPCODE[_op.opcode] is None, f"opcode {_op.opcode:#04x} is defined twice"
    assert (_op.mnemonic, _op.modes) not in BY_SIGNATURE, f"'{_op.signature}' is defined twice"
    assert _op.has_imm == bool(_op.opcode & 1), f"'{_op.signature}': odd opcodes (and only odd opcodes) take an immediate"
    assert _op.modes.count(IMM) <= 1 and len(_op.modes) - _op.modes.count(IMM) <= 2, f"'{_op.signature}' does not fit the encoding"
    BY_OPCODE[_op.opcode] = _op
    BY_SIGNATURE[_op.mnemonic, _op.modes] = _op


def disassemble(word: int, imm: int) -> str:
    """Disassemble an instruction word (and the word following it, used only if the opcode takes one)."""
    op = BY_OPCODE[word >> 8]
    if op is None:
        return f"??? (unknown opcode 0x{word >> 8:02x})"
    return op.format(word & 0xF, (word >> 4) & 0xF, imm)


if __name__ == "__main__":
    # print the opcode map
    print("opcode  instruction      encoding")
    print("------  ---------------  -----------------------------------")
    for op in ISA:
        registers = len(op.modes) - op.has_imm
        fields = f"{'bbbb' if registers > 1 else '----'} {'aaaa' if registers > 0 else '----'}"
        print(f"0x{op.opcode:02x}    {op.signature:<15}  {op.opcode:08b} {fields}{' iiiiiiii iiiiiiii' if op.has_imm else ''}")
    print(f"\n{len(ISA)} opcodes, {len(MNEMONICS)} instructions.")

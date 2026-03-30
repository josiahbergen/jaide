"""Assembler tests: assemble known .jasm snippets, compare byte output."""

import os
import tempfile

from jasm.jasm import assemble
from common.isa import OPCODE_MAP, INSTRUCTIONS, MODES, REGISTERS


def _assemble_to_bytes(source: str) -> bytes:
    """Assemble a JASM source string and return the raw binary bytes."""
    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, "test.jasm")
        bin_path = os.path.join(tmp, "test.bin")
        with open(src_path, "w") as f:
            f.write(source)
        assemble(src_path, bin_path)
        with open(bin_path, "rb") as f:
            return f.read()


def _opcode(instr: INSTRUCTIONS, modes: tuple[MODES, ...]) -> int:
    return OPCODE_MAP[(instr, modes)]


class TestNop:

    def test_nop_encoding(self):
        data = _assemble_to_bytes("nop")
        opcode = _opcode(INSTRUCTIONS.NOP, ())
        assert data == bytes([0x00, opcode])


class TestMov:

    def test_mov_reg_imm(self):
        data = _assemble_to_bytes("mov A, 0x1234")
        opcode = _opcode(INSTRUCTIONS.MOV, (MODES.REG, MODES.IMM))
        # reg_a = dest = A(0), in ssss slot → high nibble = 0
        # reg_b = None → low nibble = 0
        assert data[0] == (REGISTERS.A << 4) | 0  # register byte
        assert data[1] == opcode
        # immediate: 0x1234 little-endian → 0x34, 0x12
        assert data[2] == 0x34
        assert data[3] == 0x12

    def test_mov_reg_reg(self):
        data = _assemble_to_bytes("mov A, B")
        opcode = _opcode(INSTRUCTIONS.MOV, (MODES.REG, MODES.REG))
        # reg_a = ssss = src = B(1), reg_b = dddd = dest = A(0)
        assert data[0] == (REGISTERS.B << 4) | REGISTERS.A
        assert data[1] == opcode
        assert len(data) == 2  # no immediate


class TestAluEncoding:

    def test_add_reg_reg(self):
        data = _assemble_to_bytes("add A, B")
        opcode = _opcode(INSTRUCTIONS.ADD, (MODES.REG, MODES.REG))
        # ssss=B(1, src), dddd=A(0, dest)
        assert data[0] == (REGISTERS.B << 4) | REGISTERS.A
        assert data[1] == opcode
        assert len(data) == 2

    def test_add_reg_imm(self):
        data = _assemble_to_bytes("add A, 0x00FF")
        opcode = _opcode(INSTRUCTIONS.ADD, (MODES.REG, MODES.IMM))
        assert data[0] == (0 << 4) | REGISTERS.A  # ssss=0 (no src reg), dddd=A
        assert data[1] == opcode
        assert data[2] == 0xFF
        assert data[3] == 0x00

    def test_sub_reg_imm(self):
        data = _assemble_to_bytes("sub C, 0x0010")
        opcode = _opcode(INSTRUCTIONS.SUB, (MODES.REG, MODES.IMM))
        assert data[0] == (0 << 4) | REGISTERS.C
        assert data[1] == opcode
        assert data[2] == 0x10
        assert data[3] == 0x00


class TestPushPop:

    def test_push_reg(self):
        data = _assemble_to_bytes("push A")
        opcode = _opcode(INSTRUCTIONS.PUSH, (MODES.REG,))
        # reg_a = ssss = A(0)
        assert data[0] == (REGISTERS.A << 4) | 0
        assert data[1] == opcode
        assert len(data) == 2

    def test_pop_reg(self):
        data = _assemble_to_bytes("pop B")
        opcode = _opcode(INSTRUCTIONS.POP, (MODES.REG,))
        # reg_b = dddd = B(1)
        assert data[0] == (0 << 4) | REGISTERS.B
        assert data[1] == opcode
        assert len(data) == 2

    def test_push_imm(self):
        data = _assemble_to_bytes("push 0xABCD")
        opcode = _opcode(INSTRUCTIONS.PUSH, (MODES.IMM,))
        assert data[1] == opcode
        assert data[2] == 0xCD
        assert data[3] == 0xAB


class TestMultiInstruction:

    def test_two_instructions_size(self):
        data = _assemble_to_bytes("nop\nnop")
        nop_opcode = _opcode(INSTRUCTIONS.NOP, ())
        assert len(data) == 4  # 2 words = 4 bytes
        assert data[1] == nop_opcode
        assert data[3] == nop_opcode

    def test_mov_then_add_size(self):
        data = _assemble_to_bytes("mov A, 0x0001\nadd A, 0x0002")
        # mov reg,imm = 4 bytes + add reg,imm = 4 bytes
        assert len(data) == 8

"""Assembler tests: multi-instruction sequencing and sizing.

Per-opcode encoding is covered exhaustively by test_binary_encoding.py.
These tests focus on behaviour that only manifests across multiple instructions.
"""

import os
import tempfile

from common.isa import INSTRUCTIONS, MODES, OPCODE_MAP
from jasm.jasm import assemble


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

    def test_data_label_and_define_absolute_words(self):
        """Identifiers in data resolve to one 16-bit word (define or label address)."""
        src = (
            "define magic 0x4242\n"
            "target:\n"
            "    nop\n"
            "ptr:\n"
            "    data magic, target, 0\n"
        )
        data = _assemble_to_bytes(src)
        # nop = 1 word (2 bytes), then 3 data words (6 bytes): magic, abs target, 0
        assert len(data) == 8
        assert data[0:2] == bytes([0x00, _opcode(INSTRUCTIONS.NOP, ())])
        assert data[2:4] == bytes([0x42, 0x42])  # 0x4242 LE
        assert data[4:6] == bytes([0x00, 0x00])  # target at PC 0
        assert data[6:8] == bytes([0x00, 0x00])

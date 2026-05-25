"""Assembler tests: multi-instruction sequencing and sizing.

Per-opcode encoding is covered exhaustively by test_binary_encoding.py.
These tests focus on behaviour that only manifests across multiple instructions.
"""

import os
import tempfile

import pytest

from common.isa import INSTRUCTIONS, MODES, OPCODE_MAP
from jasm.jasm import assemble, assemble_string


def _assemble_to_bytes(source: str) -> bytes:
    """Assemble a JASM source string and return the raw binary bytes."""
    return assemble_string(source)


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


class TestMacros:

    def test_macro_single_nop_expands(self):
        # macro with one arg that wraps a NOP (simplest possible body)
        src = (
            "macro emit_nop %unused\n"
            "    nop\n"
            "end macro\n"
            "emit_nop A\n"
        )
        data = _assemble_to_bytes(src)
        nop_op = _opcode(INSTRUCTIONS.NOP, ())
        assert len(data) == 2  # one NOP = 1 word
        assert data[1] == nop_op

    def test_macro_with_arg_expands(self):
        src = (
            "macro loadval %reg\n"
            "    mov %reg, 0x0042\n"
            "end macro\n"
            "loadval A\n"
        )
        data = _assemble_to_bytes(src)
        assert len(data) == 4  # mov reg, imm = 2 words

    def test_macro_integration(self, assemble_and_load):
        src = (
            "macro double %reg\n"
            "    add %reg, %reg\n"
            "end macro\n"
            "mov A, 0x0005\n"
            "double A\n"
        )
        emu = assemble_and_load(src)
        emu.step()  # mov A, 5
        emu.step()  # add A, A (expanded from double)
        assert emu.reg["A"].value == 10

    def test_macro_multiple_instructions_in_body(self):
        # macro that emits two instructions
        src = (
            "macro inc2 %reg\n"
            "    inc %reg\n"
            "    inc %reg\n"
            "end macro\n"
            "nop\n"    # 1 word
            "inc2 A\n" # expands to 2 × inc = 2 words
        )
        data = _assemble_to_bytes(src)
        assert len(data) == 6  # 3 words total


class TestOrgDirective:

    def test_org_shifts_label_addresses(self):
        # With org 0x0010: nop is at word 0x10, mov follows at 0x11,
        # target (after the 2-word mov) lands at 0x13.
        src = (
            "org 0x0010\n"
            "nop\n"            # word 0x0010
            "mov A, target\n"  # words 0x0011-0x0012 (2-word instruction)
            "target:\n"        # word 0x0013
            "nop\n"
        )
        data = _assemble_to_bytes(src)
        # binary bytes: [0:2]=nop, [2:4]=mov header, [4:6]=imm16 (target addr)
        imm = int.from_bytes(data[4:6], "little")
        assert imm == 0x0013

    def test_org_does_not_pad_binary(self):
        # org only shifts labels; the physical binary still starts at byte 0.
        src = "org 0x0100\nnop\n"
        data = _assemble_to_bytes(src)
        assert len(data) == 2  # just the one NOP word


class TestAlignDirective:

    def test_align_pads_with_zeros(self):
        src = (
            "nop\n"      # word 0
            "align 4\n"  # pad to next 4-word boundary → 3 words of zeros
            "nop\n"      # word 4
        )
        data = _assemble_to_bytes(src)
        # 1(nop) + 3(pad) + 1(nop) = 5 words = 10 bytes
        assert len(data) == 10
        assert data[2:8] == bytes(6)  # 3 padding words

    def test_align_noop_when_already_aligned(self):
        src = (
            "nop\nnop\nnop\nnop\n"  # 4 words (already 4-aligned)
            "align 4\n"
            "nop\n"
        )
        data = _assemble_to_bytes(src)
        assert len(data) == 10  # 5 words, no extra padding inserted

    def test_align_label_placed_at_boundary(self):
        src = (
            "nop\n"      # word 0
            "align 4\n"  # pad to word 4
            "target:\n"
            "mov A, target\n"  # target should be at word 4
        )
        data = _assemble_to_bytes(src)
        # layout: nop[0:2] pad[2:8] mov_header[8:10] mov_imm16[10:12]
        imm = int.from_bytes(data[10:12], "little")
        assert imm == 4


class TestImport:

    def test_import_brings_in_constants(self):
        with tempfile.TemporaryDirectory() as tmp:
            util_path = os.path.join(tmp, "util.jasm")
            main_path = os.path.join(tmp, "main.jasm")
            bin_path  = os.path.join(tmp, "out.bin")

            with open(util_path, "w") as f:
                f.write("define MAGIC 0x00FF\n")

            import_str = util_path.replace("\\", "/")
            with open(main_path, "w") as f:
                f.write(f'import "{import_str}"\n')
                f.write("mov A, MAGIC\n")

            assemble(main_path, bin_path)
            with open(bin_path, "rb") as f:
                data = f.read()

        # mov A, imm = 2 words; imm16 = 0x00FF (little-endian: 0xFF, 0x00)
        assert len(data) == 4
        assert data[2] == 0xFF
        assert data[3] == 0x00

    def test_import_brings_in_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            util_path = os.path.join(tmp, "util.jasm")
            main_path = os.path.join(tmp, "main.jasm")
            bin_path  = os.path.join(tmp, "out.bin")

            with open(util_path, "w") as f:
                f.write("nop\n")  # one extra NOP from the imported file

            import_str = util_path.replace("\\", "/")
            with open(main_path, "w") as f:
                f.write(f'import "{import_str}"\n')
                f.write("nop\n")

            assemble(main_path, bin_path)
            with open(bin_path, "rb") as f:
                data = f.read()

        assert len(data) == 4  # util NOP + main NOP = 2 words


class TestAssemblerErrors:

    def test_undefined_label_exits(self):
        with pytest.raises(SystemExit):
            _assemble_to_bytes("jmp nowhere")

    def test_duplicate_label_exits(self):
        with pytest.raises(SystemExit):
            _assemble_to_bytes("foo:\nnop\nfoo:\nnop")

    def test_undefined_macro_exits(self):
        with pytest.raises(SystemExit):
            _assemble_to_bytes("undefined_macro A")

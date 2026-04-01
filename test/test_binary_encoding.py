"""Parametrized binary encoding tests: one test case per opcode/mode variant.

Driven entirely by OPCODE_FORMATS from common/isa.py. When the ISA changes
(opcodes added, removed, or re-encoded), the test suite adapts automatically
without any manual updates — just run pytest.
"""

import os
import tempfile

import pytest

from common.isa import OPCODE_FORMATS, InstructionFormat, MODES, REGISTERS
from jasm.jasm import assemble


# ---------------------------------------------------------------------------
# Canonical operand choices
# ---------------------------------------------------------------------------

# Register used for each operand position (by index in the operand list)
_REG_NAME = {0: "A", 1: "B"}
_REG_VAL  = {0: int(REGISTERS.A), 1: int(REGISTERS.B)}

# Immediate value used for IMM-mode operands
_CANONICAL_IMM = 0x3A33

# Label placed at the top of every generated source file.
# Being at the top means: label word-address = 0, instruction word-address = 0.
# For any 2-word instruction: next_pc = 0 + 2 = 2, so relative offset = (0 - 2) & 0xFFFF = 0xFFFE.
_LABEL = "my_label"
_LABEL_PC = 0       # word address
_REL_OFFSET = (_LABEL_PC - 2) & 0xFFFF  # 0xFFFE


def _mode_to_source(mode: MODES, op_index: int) -> str:
    """Return the JASM text fragment for a single operand."""
    if mode == MODES.REG:
        return _REG_NAME[op_index]
    if mode == MODES.IMM:
        return f"0x{_CANONICAL_IMM:04X}"
    if mode == MODES.RELATIVE:
        return _LABEL
    if mode == MODES.REG_POINTER:
        return f"[{_REG_NAME[op_index]}]"
    if mode == MODES.REL_POINTER:
        return f"[{_LABEL}]"
    if mode == MODES.OFF_POINTER:
        return f"[{_LABEL} + {_REG_NAME[op_index]}]"
    raise ValueError(f"unhandled mode: {mode}")


def _make_source(fmt: InstructionFormat) -> str:
    """Generate a complete, valid JASM source string for the given format."""
    operands = [_mode_to_source(m, i) for i, m in enumerate(fmt.modes)]
    mnemonic = fmt.mnemonic.name.lower()
    instr = mnemonic + (" " + ", ".join(operands) if operands else "")
    # Label is always at the top so its word-address resolves to 0.
    return f"{_LABEL}:\n    {instr}"


def _compute_expected(opcode: int, fmt: InstructionFormat) -> bytes:
    """Compute the expected binary bytes by applying the format encoding rules."""
    src_operand = _REG_VAL[fmt.src_operand] if fmt.src_operand is not None else 0
    dest_operand = _REG_VAL[fmt.dest_operand] if fmt.dest_operand is not None else 0

    result = bytearray()
    result.append((src_operand << 4) | dest_operand)  # [ssss | dddd]
    result.append(opcode)

    if fmt.imm_operand is not None:
        imm_mode = fmt.modes[fmt.imm_operand]
        if imm_mode == MODES.IMM:
            imm_val = _CANONICAL_IMM
        else:
            # RELATIVE, REL_POINTER, OFF_POINTER all encode a PC-relative word offset
            imm_val = _REL_OFFSET  # 0xFFFE

        result.append(imm_val & 0xFF)
        result.append((imm_val >> 8) & 0xFF)

    return bytes(result)


def _assemble_source(source: str) -> bytes:
    """Write source to a temp file, run the full assembler, return raw bytes."""
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "test.jasm")
        out = os.path.join(tmp, "test.bin")
        with open(src, "w") as f:
            f.write(source)
        assemble(src, out)
        with open(out, "rb") as f:
            return f.read()


# ---------------------------------------------------------------------------
# Parametrized test — one case per opcode in the ISA
# ---------------------------------------------------------------------------

_params = list(OPCODE_FORMATS.items())
_ids = [
    f"{fmt.mnemonic.name}_{'_'.join(m.name for m in fmt.modes) or 'none'}"
    for _, fmt in _params
]


@pytest.mark.parametrize("opcode,fmt", _params, ids=_ids)
def test_opcode_encoding(opcode: int, fmt: InstructionFormat):
    source = _make_source(fmt)
    expected = _compute_expected(opcode, fmt)
    result = _assemble_source(source)
    assert result == expected, (
        f"\nSource:\n{source}\n"
        f"Expected: {expected.hex(' ')}\n"
        f"Got:      {result.hex(' ')}"
    )

"""ISA table consistency tests.

Previously these assembled one snippet per opcode and checked the binary output.
That round-trip took ~14 ms per test (dominated by Lark grammar initialisation).
The assembler encoding pipeline is already exercised end-to-end by
test_instructions.py; what matters here is that the ISA tables are
internally coherent:

  - OPCODE_FORMATS and OPCODE_MAP are exact inverses of each other.
  - Operand indices are in range and point to modes of the expected class.
  - Every opcode is a valid byte value.
  - No two (mnemonic, modes) pairs share an opcode.
"""

import pytest

from common.isa import INSTRUCTIONS, MODES, OPCODE_FORMATS, OPCODE_MAP, InstructionFormat

# Modes that carry an immediate word in the second instruction word.
_IMM_MODES = {MODES.IMM, MODES.RELATIVE, MODES.REL_POINTER, MODES.OFF_POINTER}

# Modes that are encoded in a register nibble (ssss or dddd).
_REG_MODES = {MODES.REG, MODES.REG_POINTER}

_params = list(OPCODE_FORMATS.items())
_ids = [
    f"{fmt.mnemonic.name}_{'_'.join(m.name for m in fmt.modes) or 'none'}"
    for _, fmt in _params
]


@pytest.mark.parametrize("opcode,fmt", _params, ids=_ids)
def test_opcode_format_consistency(opcode: int, fmt: InstructionFormat):
    n = len(fmt.modes)

    # Opcode fits in one byte.
    assert 0 <= opcode <= 0xFF

    # OPCODE_MAP is the exact inverse of OPCODE_FORMATS.
    key = (fmt.mnemonic, fmt.modes)
    assert key in OPCODE_MAP, f"OPCODE_MAP missing key {key}"
    assert OPCODE_MAP[key] == opcode, (
        f"OPCODE_MAP[{key}] == {OPCODE_MAP[key]}, expected {opcode}"
    )

    # Operand indices are within the modes tuple.
    for label, idx in (("src", fmt.src_operand), ("dest", fmt.dest_operand), ("imm", fmt.imm_operand)):
        if idx is not None:
            assert 0 <= idx < n, f"{label}_operand index {idx} out of range (n={n})"

    # imm_operand must point to an immediate-class mode.
    if fmt.imm_operand is not None:
        assert fmt.modes[fmt.imm_operand] in _IMM_MODES, (
            f"imm_operand {fmt.imm_operand} points to non-immediate mode "
            f"{fmt.modes[fmt.imm_operand]}"
        )

    # src/dest operands must point to register-class modes.
    for label, idx in (("src", fmt.src_operand), ("dest", fmt.dest_operand)):
        if idx is not None:
            assert fmt.modes[idx] in _REG_MODES, (
                f"{label}_operand {idx} points to non-register mode {fmt.modes[idx]}"
            )


def test_no_duplicate_opcodes():
    assert len(OPCODE_FORMATS) == len(set(OPCODE_FORMATS.keys()))


def test_opcode_map_and_formats_same_size():
    assert len(OPCODE_MAP) == len(OPCODE_FORMATS)

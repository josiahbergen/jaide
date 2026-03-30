from common.isa import INSTRUCTIONS, INSTRUCTION_MODES, _FORMAT_DATA


def test_each_instruction_has_modes_and_format_entries():
    missing_modes: list[str] = []
    missing_format: list[str] = []

    format_instructions = {instr for (instr, _modes) in _FORMAT_DATA.keys()}

    for instr in INSTRUCTIONS:
        modes = INSTRUCTION_MODES.get(instr)
        if not modes:
            missing_modes.append(instr.name)
        if instr not in format_instructions:
            missing_format.append(instr.name)

    assert not missing_modes, (
        "INSTRUCTION_MODES is missing (or empty) entries for: "
        + ", ".join(missing_modes)
    )
    assert not missing_format, (
        "_FORMAT_DATA is missing (or has no entries) for: "
        + ", ".join(missing_format)
    )


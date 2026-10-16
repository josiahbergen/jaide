# coverage.py
# generate jasm that exercises every instruction, operand form, and directive.
# josiah bergen, october 2026

import argparse
from itertools import product
from pathlib import Path

from isa import INSTRUCTION_MODES, MODES, REGISTERS

# stem must not contain "_": label references are treated as already mangled
# only when the text before "__" has no underscore.
IMPORT_NAME = "covimport.jasm"
EXTERNAL_LABEL = "covimport__imported_label"

REGISTERS_ASM: list[str] = [register.name.lower() for register in REGISTERS]

# prefixes stay lowercase. the lexer only accepts "0x" and "0b", not "0X" / "0B".
NUMBER_LITERALS: list[str] = [
    "0",
    "1",
    "00",
    "65535",
    "0x0",
    "0x00",
    "0x0000",
    "0xf",
    "0x00ff",
    "0x7fff",
    "0x8000",
    "0xffff",
    "0xFfFf",
    "0xabcd",
    "0b0",
    "0b1",
    "0b0000000000000000",
    "0b1111111111111111",
]

# counts stay 0 or 1. a large TIMES count emits that many words and will
# walk the coverage program off the end of the 16-bit address space.
SMALL_COUNTS: list[str] = ["0", "1", "0x0", "0x1", "0b0", "0b1"]

# same constraint as TIMES: alignment is a pad, so keep it small.
ALIGNMENTS: list[str] = ["1", "2", "4", "0x1", "0x2", "0x10", "0b1", "0b10"]

DEFINES: list[tuple[str, str]] = [
    ("imm_const", "0x7fff"),
    ("dec_const", "65535"),
    ("bin_const", "0b1010101010101010"),
    ("hex_const", "0x00ff"),
    ("zero_const", "0"),
    ("under_score", "0"),
    ("name2", "2"),
]

# identifiers the assembler rewrites to an immediate: defines, local labels,
# and a label imported from the companion file.
IMMEDIATE_OPERANDS: list[str] = [
    *NUMBER_LITERALS,
    *[name for name, _value in DEFINES],
    "imported_const",
    "target",
    "forward",
    EXTERNAL_LABEL,
]

# branches have no immediate form. a define here would be rewritten to IMM
# and then fail opcode lookup, so only real labels go in this list.
RELATIVE_OPERANDS: list[str] = [
    "target",
    "forward",
    EXTERNAL_LABEL,
]

STRINGS: list[str] = [
    "",
    "a",
    "A",
    "0xFFFF",
    "hello, world!",
]


def operand_choices(mode: MODES) -> list[str]:
    if mode is MODES.REG:
        return list(REGISTERS_ASM)
    if mode is MODES.REG_POINTER:
        return [f"[{name}]" for name in REGISTERS_ASM]
    if mode is MODES.IMM:
        return list(IMMEDIATE_OPERANDS)
    if mode is MODES.RELATIVE:
        return list(RELATIVE_OPERANDS)
    if mode is MODES.OFF_POINTER:
        return [f"[{label} + {name}]" for label in RELATIVE_OPERANDS for name in REGISTERS_ASM]
    if mode is MODES.REL_POINTER:
        return [f"[{label}]" for label in RELATIVE_OPERANDS]
    raise ValueError(f"no jasm spelling for {mode.name}")


def format_instruction(mnemonic: str, operands: tuple[str, ...]) -> str:
    if not operands:
        return f"    {mnemonic}"
    return f"    {mnemonic} {', '.join(operands)}"


def upper_operand(operand: str) -> str:
    # leave numeric prefixes alone. "0XFFFF" is not a NUMBER token.
    if operand.startswith("["):
        return "[" + operand[1:-1].upper() + "]"
    if operand[0].isalpha() or operand[0] == "_":
        return operand.upper()
    return operand


def instruction_lines() -> list[str]:
    lines: list[str] = []
    for mnemonic, mode_lists in INSTRUCTION_MODES.items():
        name = mnemonic.name.lower()
        for modes in mode_lists:
            choices = [operand_choices(mode) for mode in modes]
            mode_text = ", ".join(mode.name.lower() for mode in modes) or "none"
            lines.append(f"; {name} {mode_text}")
            for operands in product(*choices):
                lines.append(format_instruction(name, operands))
            first = tuple(choice[0] for choice in choices)
            lines.append(format_instruction(name.upper(), tuple(upper_operand(op) for op in first)))
            lines.append("")
    return lines


def directive_lines(import_path: str) -> list[str]:
    lines: list[str] = ["; directives", ""]

    for literal in NUMBER_LITERALS:
        lines.append(f"    org {literal}")
    # last origin wins. keep the program at 0 after the spelling sweep.
    lines.append("    org 0x0000")
    lines.append("    ORG 0x0000")
    lines.append("")

    for name, value in DEFINES:
        lines.append(f"    define {name} {value}")
    lines.append("    DEFINE upper_const 0x10")
    lines.append("")

    lines.append(f'    import "{import_path}"')
    lines.append(f'    IMPORT "{import_path}"')
    lines.append("")

    lines.append("data_numbers:")
    for literal in NUMBER_LITERALS:
        lines.append(f"    data {literal}")
    lines.append("    DATA 0x1")
    lines.append("")

    lines.append("data_strings:")
    for text in STRINGS:
        lines.append(f'    data "{text}"')
    lines.append('    data "hello, world!", 0')
    lines.append("")

    lines.append("data_symbols:")
    for name, _value in DEFINES:
        lines.append(f"    data {name}")
    lines.append("    data imported_const")
    lines.append("    data target")
    lines.append("    data forward")
    lines.append(f"    data {EXTERNAL_LABEL}")
    lines.append(f'    data 1, 0x2, 0b11, "hi", target, imm_const, {EXTERNAL_LABEL}')
    lines.append("")

    lines.append("; times")
    for count in SMALL_COUNTS:
        for value in NUMBER_LITERALS:
            lines.append(f"    times {count}, {value}")
    lines.append("    TIMES 1, 0")
    lines.append("")

    lines.append("; align")
    for alignment in ALIGNMENTS:
        lines.append(f"    align {alignment}")
    lines.append("    ALIGN 0x2")
    lines.append("")
    return lines


def break_lines() -> list[str]:
    # break marks the next instruction, skipping a following label, data, or align.
    return [
        "; break",
        "    break",
        "    nop",
        "    BREAK",
        "break_label:",
        "    nop",
        "    break",
        "    data 0x1",
        "    nop",
        "    break",
        "    align 0x2",
        "    nop",
        "",
    ]


def spelling_lines() -> list[str]:
    return [
        "; spelling",
        "    mov  a,   b",
        "    mov a,b",
        "    MoV a, B",
        "    nop ; comment",
        "",
    ]


def generate_jasm(import_path: str) -> str:
    lines = [
        "; generated by common.coverage. do not edit.",
        "; every legal instruction mode, every register, every immediate spelling,",
        "; and every directive form.",
        "; import paths are resolved from the working directory.",
        "",
        *directive_lines(import_path),
        "target:",
        *instruction_lines(),
        *spelling_lines(),
        *break_lines(),
        "forward:",
        "    nop",
        "    halt",
        "",
    ]
    return "\n".join(lines)


def generate_import() -> str:
    return "\n".join([
        "; imported by the jasm file from common.coverage.",
        "define imported_const 0x1234",
        "",
        "imported_label:",
        "    nop",
        "",
    ])


def write(output: Path) -> Path:
    """Write the coverage program and its imported companion. Returns the companion path."""
    output.parent.mkdir(parents=True, exist_ok=True)
    companion = output.parent / IMPORT_NAME
    output.write_text(generate_jasm(companion.as_posix()) + "\n", encoding="utf-8", newline="\n")
    companion.write_text(generate_import(), encoding="utf-8", newline="\n")
    return companion


def main() -> None:
    parser = argparse.ArgumentParser(description="generate jasm covering every instruction, operand, and directive")
    parser.add_argument("-o", "--output", type=Path, default=Path("coverage.jasm"))
    args = parser.parse_args()
    companion = write(args.output)
    print(f"wrote {args.output}")
    print(f"wrote {companion}")


if __name__ == "__main__":
    main()

# isa.py
# shared isa definitions for the jaide project.
# josiah bergen, march 2026

# Re-export everything from the canonical common ISA so jasm and jaide
# always share exactly one definition.
# RTYPE is only needed by the assembler for operand-direction annotation.
from enum import IntEnum

from common.isa import (
    INSTRUCTION_MODES,
    INSTRUCTIONS,
    MODES,
    OPCODE_FORMATS,
    OPCODE_MAP,
    OPCODE_MAP_KEYS,
    REGISTERS,
    InstructionFormat,
    generate_opcode_string,
)


class RTYPE(IntEnum):
    SRC  = 0
    DEST = 1

__all__ = [
    "INSTRUCTIONS",
    "REGISTERS",
    "MODES",
    "INSTRUCTION_MODES",
    "OPCODE_MAP_KEYS",
    "OPCODE_MAP",
    "InstructionFormat",
    "OPCODE_FORMATS",
    "generate_opcode_string",
    "RTYPE",
]

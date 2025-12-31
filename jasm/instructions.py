# instructions.py
# instruction utilities and helpers.
# josiah bergen, december 2025

from .language.constants import OPCODES, OPERAND_TYPES, ADDRESSING_MODES
from .util.logger import logger


def get_addressing_mode(mnemonic, operands):
    """
    Get the addressing mode for an instruction.
    """
    scope = "language.py:get_addressing_mode()"

    if mnemonic not in OPCODES.keys():
        logger.fatal(f"unknown mnemonic: {mnemonic}", scope)
    if not all(op.type in OPERAND_TYPES for op in operands):
        logger.fatal(f"invalid operands: {operands}", scope)

    optypes = [OPERAND_TYPES[op.type] for op in operands]
    match mnemonic:
        # No operands
        case "SEC" | "CLC" | "CLZ" | "HALT" | "NOP":
            return ADDRESSING_MODES["NO_OPERANDS"]

        # Single register operand
        case "POP" | "INC" | "DEC" | "NOT":
            return ADDRESSING_MODES["REGISTER"]

        # Single 8-bit immediate operand
        case "INT":
            return ADDRESSING_MODES["IMM8"]

        # Single register or single 8-bit immediate operand
        case "PUSH":
            if optypes[0] == OPERAND_TYPES["NUMBER"]:
                return ADDRESSING_MODES["IMM8"]
            else:
                return ADDRESSING_MODES["REGISTER"]

        # register + register or 8-bit immediate
        case (
            "MOVE"
            | "ADD"
            | "ADDC"
            | "SUB"
            | "SUBB"
            | "SHL"
            | "SHR"
            | "AND"
            | "OR"
            | "NOR"
            | "XOR"
            | "CMP"
            | "INB"
            | "OUTB"
        ):
            if optypes[1] == OPERAND_TYPES["NUMBER"]:
                return ADDRESSING_MODES["REGISTER_IMM8"]
            else:
                return ADDRESSING_MODES["REGISTER_REGISTER"]

        # Register + 16-bit memory address or register + register pair memory address
        case "LOAD" | "STORE":
            if len(optypes) > 1 and optypes[1] == OPERAND_TYPES["REGISTER_PAIR"]:
                return ADDRESSING_MODES["REGISTER_REGPAIR_ADDRESS"]
            return ADDRESSING_MODES["REGISTER_IMM16_ADDRESS"]

        # 16-bit immediate memory address
        case "JMP" | "JZ" | "JNZ" | "JC" | "JNC":
            return ADDRESSING_MODES["IMM16"]

        case _:
            logger.fatal(f"unknown addressing mode for {mnemonic}", scope)

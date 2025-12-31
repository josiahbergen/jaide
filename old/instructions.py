"""
Instruction definitions, opcodes, validation, and size calculation for JASM.
"""

from .language.constants import OPERAND_TYPES, OPERAND_TYPE_TO_STRING, ADDRESSING_MODES, ADDRESSING_MODE_TO_SIZE

def get_operands(node):
    # safely get operands
    if len(node.children) > 1 and node.children[1].data == "operand_list":
        return node.children[1].children
    else:
        return []


def validate_instruction_semantics(node):
    """
    Validate that an instruction has the correct number and types of operands.
    """
    scope = "instructions.py:validate_instruction_semantics()"

    def validate_num_operands(required_num, actual_num, mnemonic, current_line):
        if actual_num != required_num:
            logger.error(
                f"{mnemonic} instruction requires {required_num} operands. Got {actual_num} on line {current_line}."
            )

    def validate_operand_type(
        operand_type, operand_index, expected_types, mnemonic, current_line
    ):
        if operand_type not in expected_types:
            logger.error(
                f"{mnemonic} instruction requires "
                + f"{', '.join(OPERAND_TYPE_TO_STRING[t] for t in expected_types)} "
                + f"as operand {operand_index + 1}. Got {OPERAND_TYPE_TO_STRING[operand_type]} "
                + f"on line {current_line}."
            )

    mnemonic = node.children[0].value.upper()
    line = node.children[0].line

    # Handle optional operand_list
    operands = get_operands(node)
    optypes = [OPERAND_TYPES[op.type] for op in operands]

    match mnemonic:
        case "SEC" | "CLC" | "CLZ" | "HALT" | "NOP":
            # 0 operands
            validate_num_operands(0, len(optypes), mnemonic, line)
            logger.verbose(
                f"    Validated instruction semantics for {mnemonic} on line {line}: 0 operands"
            )
        case "INT":
            # 1 operand (number)
            validate_num_operands(1, len(optypes), mnemonic, line)
            validate_operand_type(
                optypes[0], 0, [OPERAND_TYPES["NUMBER"]], mnemonic, line
            )
            logger.verbose(
                f"    Validated instruction semantics for {mnemonic} on line {line}: 1 operand (number)"
            )
        case "POP" | "INC" | "DEC" | "NOT":
            # 1 operand (register)
            validate_num_operands(1, len(optypes), mnemonic, line)
            validate_operand_type(
                optypes[0], 0, [OPERAND_TYPES["REGISTER"]], mnemonic, line
            )
            logger.verbose(
                f"    Validated instruction semantics for {mnemonic} on line {line}: 1 operand (register)"
            )
        case "PUSH":
            # 1 operand (register or number)
            validate_num_operands(1, len(optypes), mnemonic, line)
            validate_operand_type(
                optypes[0],
                0,
                [OPERAND_TYPES["REGISTER"], OPERAND_TYPES["NUMBER"]],
                mnemonic,
                line,
            )
            logger.verbose(
                f"    Validated instruction semantics for {mnemonic} on line {line}: 1 operand (register/number)"
            )
        case "JMP" | "JZ" | "JNZ" | "JC" | "JNC":
            # 1 operand (labelname, number or register pair)
            validate_num_operands(1, len(optypes), mnemonic, line)
            validate_operand_type(
                optypes[0],
                0,
                [OPERAND_TYPES["LABELNAME"], OPERAND_TYPES["NUMBER"]],
                mnemonic,
                line,
            )
            logger.verbose(
                f"    Validated instruction semantics for {mnemonic} on line {line}: 1 operand (labelname/number/register pair)"
            )
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
            | "INB"
            | "OUTB"
            | "CMP"
        ):
            # 2 operands (register, register or number)
            validate_num_operands(2, len(optypes), mnemonic, line)
            validate_operand_type(
                optypes[0], 0, [OPERAND_TYPES["REGISTER"]], mnemonic, line
            )
            validate_operand_type(
                optypes[1],
                1,
                [OPERAND_TYPES["REGISTER"], OPERAND_TYPES["NUMBER"]],
                mnemonic,
                line,
            )
            logger.verbose(
                f"    Validated instruction semantics for {mnemonic} on line {line}: 2 operands (register, register/number)"
            )
        case "LOAD" | "STORE":
            # 2 operands (register, number or register pair)
            validate_num_operands(2, len(optypes), mnemonic, line)
            validate_operand_type(
                optypes[0], 0, [OPERAND_TYPES["REGISTER"]], mnemonic, line
            )
            validate_operand_type(
                optypes[1],
                1,
                [OPERAND_TYPES["NUMBER"], OPERAND_TYPES["REGISTER_PAIR"]],
                mnemonic,
                line,
            )
            logger.verbose(
                f"    Validated instruction semantics for {mnemonic} on line {line}: 2 operands (register, number/register pair)"
            )
        case _:
            logger.error(f"Unknown instruction: {mnemonic} on line {line}")


def get_addressing_mode(mnemonic, operands):
    """
    Get the addressing mode for an instruction.
    """
    global logger
    scope = "instructions.py:get_addressing_mode()"

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
            logger.error(f"Unknown addressing mode for {mnemonic}", scope)


def get_instruction_size(mnemonic, operands, logger):
    mnemonic = mnemonic.upper()

    addressing_mode = get_addressing_mode(mnemonic, operands)
    logger.verbose(
        f"    Instruction size for {mnemonic} defined as {ADDRESSING_MODE_TO_SIZE[addressing_mode]}"
    )
    if addressing_mode is None:
        return None
    return ADDRESSING_MODE_TO_SIZE[addressing_mode]

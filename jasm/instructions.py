"""
Instruction definitions, opcodes, validation, and size calculation for JASM.
"""

OPCODES = {
    "LOAD": 0x0,
    "STORE": 0x1,
    "MOVE": 0x2,
    "PUSH": 0x3,
    "POP": 0x4,
    "ADD": 0x5,
    "ADDC": 0x6,
    "SUB": 0x7,
    "SUBB": 0x8,
    "INC": 0x9,
    "DEC": 0xA,
    "LSH": 0xB,
    "RSH": 0xC,
    "AND": 0xD,
    "OR": 0xE,
    "NOR": 0xF,
    "NOT": 0x10,
    "XOR": 0x11,
    "INB": 0x12,
    "OUTB": 0x13,
    "CMP": 0x14,
    "SEC": 0x15,
    "CLC": 0x16,
    "CLZ": 0x17,
    "JUMP": 0x18,
    "JZ": 0x19,
    "JNZ": 0x1A,
    "JC": 0x1B,
    "JNC": 0x1C,
    "INT": 0x1D,
    "HALT": 0x1E,
    "NOP": 0x1F,
}

REGISTERS = {
    # General purpose registers
    "A": 0x0,  # General purpose / accumulator
    "B": 0x1,  # General purpose
    "C": 0x2,  # General purpose
    "D": 0x3,  # General purpose
    "X": 0x4,  # Low address / general purpose
    "Y": 0x5,  # High address / general purpose
    # Memory-mapped registers
    "F": 0x6,  # Flags
    "Z": 0x7,  # Zero
    "PC": 0x8,  # Program Counter (read-only)
    "SP": 0x9,  # Stack Pointer
    "MB": 0xA,  # Memory Bank
    "STS": 0xB,  # Status
}

OPERAND_TYPES = {
    "LABELNAME": 0,
    "NUMBER": 1,
    "REGISTER": 2,
    "REGISTER_PAIR": 3,
}

OPERAND_TYPE_TO_STRING = {
    OPERAND_TYPES["LABELNAME"]: "LABELNAME",
    OPERAND_TYPES["NUMBER"]: "NUMBER",
    OPERAND_TYPES["REGISTER"]: "REGISTER",
    OPERAND_TYPES["REGISTER_PAIR"]: "REGISTER_PAIR",
}

ADDRESSING_MODES = {
    "NO_OPERANDS": 0,
    "REGISTER": 1,
    "IMM8": 2,
    "REGISTER_REGISTER": 3,
    "REGISTER_IMM8": 4,
    "REGISTER_IMM16_ADDRESS": 5,
    "REGISTER_REGPAIR_ADDRESS": 6,
    "IMM16": 7,
}

ADDRESSING_MODE_TO_SIZE = {
    ADDRESSING_MODES["NO_OPERANDS"]: 1,
    ADDRESSING_MODES["REGISTER"]: 2,
    ADDRESSING_MODES["IMM8"]: 3,
    ADDRESSING_MODES["REGISTER_REGISTER"]: 2,
    ADDRESSING_MODES["REGISTER_IMM8"]: 3,
    ADDRESSING_MODES["REGISTER_IMM16_ADDRESS"]: 4,
    ADDRESSING_MODES["REGISTER_REGPAIR_ADDRESS"]: 3,
    ADDRESSING_MODES["IMM16"]: 4,
}


def get_operands(node):
    # safely get operands
    if len(node.children) > 1 and node.children[1].data == "operand_list":
        return node.children[1].children
    else:
        return []


def validate_instruction_semantics(node, logger):
    """
    Validate that an instruction has the correct number and types of operands.
    """

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
            return None


def get_instruction_size(mnemonic, operands, logger):
    mnemonic = mnemonic.upper()

    addressing_mode = get_addressing_mode(mnemonic, operands)
    logger.verbose(
        f"    Instruction size for {mnemonic} defined as {ADDRESSING_MODE_TO_SIZE[addressing_mode]}"
    )
    if addressing_mode is None:
        return None
    return ADDRESSING_MODE_TO_SIZE[addressing_mode]

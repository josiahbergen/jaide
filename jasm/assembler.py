"""
Core assembly logic: label resolution and binary generation.
"""

from lark import Token

from .instructions import (
    OPCODES,
    REGISTERS,
    get_addressing_mode,
    get_instruction_size,
    get_operands,
    validate_instruction_semantics,
)

def resolve_labels(tree, logger):
    """
    Pass 1: Resolve all labels and calculate their addresses.
    Returns a dictionary mapping label names to addresses.
    """
    logger.debug("Resolving labels...")
    labels = {}
    pc = 0

    for node in tree.children:
        # Skip comments
        if isinstance(node, Token) and node.type == "COMMENT":
            continue

        if not hasattr(node, "data"):
            logger.error(
                f"Node has no data: {node}. Perhaps you have an empty start label?"
            )

        if node.data == "label":
            label_name = node.children[0].value

            if labels.get(label_name):
                logger.error(f"Label {label_name} already defined. Exiting...")

            labels[label_name] = pc
            logger.debug(f"Found label: {label_name} (at {pc})")
            continue

        if node.data == "instr":
            validate_instruction_semantics(node, logger)
            mnemonic = node.children[0].value.upper()
            operands = get_operands(node)

            # get instruction size
            size = get_instruction_size(mnemonic, operands, logger)
            if size is None:
                logger.error(
                    f"Bad instruction: {mnemonic} on line {node.children[0].line}"
                )
            pc += size
            logger.verbose(
                f"    Finished processing instruction {mnemonic} at PC={pc - size}, size={size} bytes"
            )

    logger.debug(f"Finished resolving {len(labels)} labels:")
    for label, address in labels.items():
        logger.debug(f"    {label} = {address}")

    return labels


def get_operand_value(operand, labels, logger):
    def get_number_value(value):
        # turn number string into an integer
        value = value.strip()

        if value.lower().startswith("0x"):
            # hex
            return int(value, 16)
        elif value.lower().startswith("b"):
            # binary
            return int(value[1:], 2)
        else:
            # decimal
            return int(value, 10)

    def get_register_value(reg_name, logger):
        # get register value from register name
        reg_val = REGISTERS.get(reg_name.upper())
        if reg_val is None:
            logger.error(f"Unknown register: {reg_name}")
        return reg_val

    def get_register_pair_value(pair_str, logger):
        # split register pair string into two register values
        parts = pair_str.split(":")
        if len(parts) != 2:
            logger.error(f"Invalid register pair: {pair_str}")
        # encode each register
        reg1 = get_register_value(parts[0].strip(), logger)
        reg2 = get_register_value(parts[1].strip(), logger)
        return reg1, reg2

    def get_label_value(label_name, labels, logger):
        # get label value (i.e. address) from label name
        if label_name not in labels:
            logger.error(f"Unknown label: {label_name}")
        return labels[label_name]

    value = None
    if operand.type == "REGISTER":
        value = get_register_value(operand.value.strip(), logger)

    elif operand.type == "REGISTER_PAIR":
        value = get_register_pair_value(operand.value.strip(), logger)

    elif operand.type == "NUMBER":
        value = get_number_value(operand.value.strip())

    elif operand.type == "LABELNAME":
        value = get_label_value(operand.value.strip(), labels, logger)

    else:
        logger.error(f"Unknown operand: {operand.value.strip()}")

    logger.verbose(
        f"    Encoded {operand.type} value as {value} for operand {operand.value.strip()}"
    )
    return value


def get_bytearray_bits_string(bytearray):
    string = ""
    for byte in bytearray:
        string += f"{byte:08b} "
    return string


def get_byte1_bits_string(byte):
    opcode_bits = (byte >> 3) & 0b11111
    addressing_mode_bits = byte & 0b111
    return f"{opcode_bits:05b} {addressing_mode_bits:03b} | {opcode_bits:<5} {addressing_mode_bits:<3} |"


def assert_operand_count(expected, actual, logger):
    if expected != actual:
        logger.error(f"Expected {expected} operands, got {actual}")
    return


def assert_immediate_size(expected, value, logger):
    if value >= (2**expected):
        logger.error(f"Immediate value {value} is too large for size {expected}")
    return


def generate_instruction_binary(opcode, operands, addressing_mode, line, logger):
    # generate binary for an instruction, given the opcode, addressing mode, and list of operands
    binary = bytearray()

    # format for the first byts is AAAAA BBB
    # AAAAA is the opcode
    # BBB is the addressing mode

    opcode_bits = (opcode & 0b11111) << 3
    addressing_mode_bits = addressing_mode & 0b111
    byte_1 = opcode_bits | addressing_mode_bits
    binary.append(byte_1)

    logger.verbose(
        f"    Generated first byte: {byte_1:08b} | {get_byte1_bits_string(byte_1)}"
    )

    # this is where the "simple" part ends
    # see the instruction format section in spec.md for more details on the addressing modes

    match addressing_mode:
        case 0:  # no operands, easy!
            pass

        case 1:  # single register operand
            assert_operand_count(1, len(operands), logger)
            # the first register is encoded in the high 4 bits of the byte
            byte_2 = (operands[0] & 0b00001111) << 4
            logger.verbose(
                f"    Generated second byte: {byte_2:08b}  (register: {operands[0]:04b})"
            )
            binary.append(byte_2)

        case 2:  # single 8-bit immediate operand
            assert_operand_count(1, len(operands), logger)
            assert_immediate_size(8, operands[0], logger)
            # second byte is unused
            binary.append(0b00000000)
            logger.verbose(f"    Generated second byte: {0b00000000:08b}  (unused)")
            byte_3 = operands[0]
            logger.verbose(
                f"    Generated third byte: {byte_3:08b}   (imm8: {operands[0]:08b})"
            )
            binary.append(byte_3)

        case 3:  # two register operands
            assert_operand_count(2, len(operands), logger)
            byte_2 = (operands[0] & 0b00001111) << 4 | (operands[1] & 0b00001111)
            logger.verbose(
                f"    Generated second byte: {byte_2:08b}  (register: {operands[0]:04b}, register: {operands[1]:04b})"
            )
            binary.append(byte_2)

        case 4:  # register and 8-bit immediate operand
            assert_operand_count(2, len(operands), logger)
            assert_immediate_size(8, operands[1], logger)
            byte_2 = (
                operands[0] & 0b00001111
            ) << 4  # register goes into the high 4 bits
            logger.verbose(
                f"    Generated second byte: {byte_2:08b}  (register: {operands[0]:04b}, imm8: {operands[1]:08b})"
            )
            binary.append(byte_2)
            byte_3 = operands[1]
            logger.verbose(
                f"    Generated third byte: {byte_3:08b}   (imm8: {operands[1]:08b})"
            )
            binary.append(byte_3)

        case 5:  # register and 16-bit immediate operand
            assert_operand_count(2, len(operands), logger)
            assert_immediate_size(16, operands[1], logger)
            byte_2 = (operands[0] & 0b00001111) << 4
            logger.verbose(
                f"    Generated second byte: {byte_2:08b}  (register: {(operands[0] & 0b00001111):04b})"
            )
            binary.append(byte_2)

            # little endian encoding
            byte_3 = operands[1] & 0b0000000011111111
            logger.verbose(
                f"    Generated third byte: {byte_3:08b}   (imm16 low byte: {byte_3:08b})"
            )
            binary.append(byte_3)
            byte_4 = operands[1] >> 8
            logger.verbose(
                f"    Generated fourth byte: {byte_4:08b}  (imm16 high byte: {byte_4:08b})"
            )
            binary.append(byte_4)

        case 6:  # register and register pair operand
            assert_operand_count(2, len(operands), logger)

            # byte 2 is the lonely register (operand 0)
            byte_2 = (operands[0] & 0b00001111) << 4
            logger.verbose(
                f"    Generated second byte: {byte_2:08b}  (register: {(operands[0] & 0b00001111):04b})"
            )
            binary.append(byte_2)

            # byte three is the register pair (operand 1)
            byte_3 = (operands[1][0] & 0b00001111) << 4 | (operands[1][1] & 0b00001111)
            logger.verbose(
                f"    Generated third byte: {byte_3:08b}  (register pair: {(operands[1][0] & 0b00001111):04b}, {(operands[1][1] & 0b00001111):04b})"
            )
            binary.append(byte_3)

        case 7:  # 16-bit immediate operand
            assert_operand_count(1, len(operands), logger)
            assert_immediate_size(16, operands[0], logger)

            # byte 2 is unused
            binary.append(0b00000000)
            logger.verbose(f"    Generated second byte: {0b00000000:08b}  (unused)")

            # little endian encoding

            # low 8 bits if the immediate
            byte_3 = operands[0] & 0b0000000011111111
            logger.verbose(
                f"    Generated third byte: {byte_3:08b}  (imm16 low byte: {byte_3:08b})"
            )
            binary.append(byte_3)

            # high 8 bits if the immediate
            byte_4 = operands[0] >> 8
            logger.verbose(
                f"    Generated fourth byte: {byte_4:08b}   (imm16 high byte: {byte_4:08b})"
            )
            binary.append(byte_4)

    return binary


def encode_instruction(node, labels, pc, logger):
    # encode the instruction into a binary
    mnemonic = node.children[0].value.upper()
    line = node.children[0].line
    opcode = OPCODES[mnemonic]
    tree_operands = get_operands(node)
    addressing_mode = get_addressing_mode(mnemonic, tree_operands)
    expected_size = get_instruction_size(mnemonic, tree_operands, logger)

    logger.verbose(f"Generating binary for instruction {mnemonic} (line {line})...")

    operands = []

    for operand in tree_operands:
        operands.append(get_operand_value(operand, labels, logger))

    logger.verbose(
        f"    Got opcode={opcode}, operands={operands}, addressing_mode={addressing_mode}"
    )
    binary_instruction = generate_instruction_binary(
        opcode, operands, addressing_mode, line, logger
    )

    logger.debug(
        f"Binary: | PC 0x{pc:04X} | {mnemonic:<5} | "
        f"{get_bytearray_bits_string(binary_instruction):<36}| {binary_instruction.hex()}"
    )

    if len(binary_instruction) != expected_size:
        logger.error(
            f"Instruction {node.children[0].value.upper()} (line {line}) "
            f"not encoded correctly (expected size {expected_size}, got {len(binary_instruction)})"
        )
        exit(1)

    return binary_instruction


def generate_binary(tree, labels, logger):
    logger.debug(f"Starting code generation for {len(tree.children)} instructions...")
    binary = bytearray()

    for node in tree.children:
        if isinstance(node, Token) and node.type == "COMMENT":
            continue

        if node.data == "label":
            continue

        if node.data == "instr":
            binary.extend(encode_instruction(node, labels, len(binary), logger))

    return binary

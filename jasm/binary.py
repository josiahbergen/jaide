# binary.py
# binary generation functions.
# josiah bergen, december 2025

from .language.context import AssemblyContext
from .language.ir.base import DataDirectiveNode, InstructionNode, Operand
from .language.ir.operands import (
    ImmediateOperand,
    LabelOperand,
    OffsetPointerOperand,
    RelativePointerOperand,
)
from .language.isa import INSTRUCTIONS, MODES, OPCODE_FORMATS
from .util.logger import logger


def generate_binary(context: AssemblyContext) -> bytearray:
    """Generate a binary string from the IR."""

    binary = bytearray()
    for node in context.ir:
        old_len = len(binary)

        if isinstance(node, DataDirectiveNode):
            binary.extend(node.encode())

        elif isinstance(node, InstructionNode):
            binary.extend(encode_instruction(node, context))

        else:
            pass  # label, no code to generate

        logger.debug(f"bytes: finished generating {len(binary) - old_len} bytes for {node} on line {node.line} (0x{node.pc:04X})")

    logger.debug(f"binary: generation finished ({len(binary)} bytes)")

    return binary


def encode_instruction(node: InstructionNode, context: AssemblyContext) -> bytearray:
    scope = "binary.py:encode_instruction()"

    if not context.linkable and node.mnemonic == INSTRUCTIONS.JMP and node.operands[0].mode == MODES.IMM:
        logger.fatal(f"jump to absolute address on line {node.line}. use --bios-mode to enable low-level functionality.", scope)

    fmt = OPCODE_FORMATS[node.opcode]

    # Extract register values from the operands identified in the format.
    # reg_a → ssss (high nibble), reg_b → dddd (low nibble).
    reg_a = 0
    reg_b = 0

    if fmt.reg_a is not None:
        reg_a = node.operands[fmt.reg_a].get_value()

    if fmt.reg_b is not None:
        reg_b = node.operands[fmt.reg_b].get_value()

    # Compute immediate value, if this opcode has one.
    immediate_value = None
    if fmt.imm is not None:
        immediate_value = compute_immediate(node, node.operands[fmt.imm], context)

    logger.verbose(f"binary: registers: {reg_a << 4 | reg_b:08b} | {reg_a:04b} {reg_b:04b} | {reg_a} {reg_b}")
    logger.verbose(f"binary: opcode:    {node.opcode:08b} | 0x{node.opcode:02X}      | {fmt.mnemonic.name}")

    if immediate_value is not None:
        logger.verbose(f"binary: immediate: {immediate_value & 0xFF:08b} | {(immediate_value >> 8) & 0xFF:08b}  | 0x{immediate_value:04X}")
        logger.verbose(f"binary: result:    {reg_a << 4 | reg_b:08b} {node.opcode:08b} {immediate_value & 0xFF:08b} {(immediate_value >> 8) & 0xFF:08b}")
    else:
        logger.verbose(f"binary: result:    {reg_a << 4 | reg_b:08b} {node.opcode:08b}")

    result = bytearray()
    result.append((reg_a << 4) | reg_b)  # register byte: [ssss | dddd]
    result.append(node.opcode)  # opcode byte

    if immediate_value is not None:
        result.append(immediate_value & 0xFF)  # low byte
        result.append((immediate_value >> 8) & 0xFF)  # high byte

    return result


def compute_immediate(node: InstructionNode, immediate: Operand, ctx: AssemblyContext) -> int | None:
    next_pc = node.pc + node.size

    if isinstance(immediate, ImmediateOperand):
        return immediate.value  # plain constant

    if isinstance(immediate, LabelOperand):
        # relative offset: encoded as (label - next_pc) mod 2^16
        label_address = ctx.labels[immediate.name]
        return (label_address - next_pc) & 0xFFFF

    if isinstance(immediate, (RelativePointerOperand, OffsetPointerOperand)):
        # [label] or [label + reg] — offset relative to next instruction
        label_address = ctx.labels[immediate.label]
        return (label_address - next_pc) & 0xFFFF

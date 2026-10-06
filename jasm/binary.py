# binary.py
# binary generation functions.
# josiah bergen, december 2025

from .language.context import AssemblyContext
from .language.ir.base import AlignDirectiveNode, BreakDirectiveNode, DataDirectiveNode, InstructionNode, Operand, TimesDirectiveNode
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
    context.source_map.reset()
    pending_breakpoint = False

    for node in context.ir:
        old_len = len(binary)

        if isinstance(node, (DataDirectiveNode, TimesDirectiveNode, AlignDirectiveNode)):
            encoded = node.encode()
            binary.extend(encoded)
            context.source_map.add_node(node, encoded)

        elif isinstance(node, InstructionNode):
            encoded = encode_instruction(node, context)
            binary.extend(encoded)
            # only consume pending breakpoints when we're encoding an instruction
            context.source_map.add_node(node, encoded, pending_breakpoint)
            pending_breakpoint = False

        else:
            if isinstance(node, BreakDirectiveNode):
                pending_breakpoint = True  # check if the next instruction needs a breakpoint

            continue  # no code to generate

        logger.verbose(f"bytes: finished generating {len(binary) - old_len} bytes for {node} on line {node.line} (0x{node.pc:04X})")

    if len(context.ir) > 0 and pending_breakpoint:
        last_node = context.ir[-1]
        logger.fatal(f"breakpoint with no associated instruction ({last_node.filename}, line {last_node.line}).", "binary.py:generate_binary()")

    logger.debug(f"binary: generation finished ({len(binary)} bytes)")

    return binary


def encode_instruction(node: InstructionNode, context: AssemblyContext) -> bytearray:
    scope = "binary.py:encode_instruction()"

    if not context.linkable and node.mnemonic == INSTRUCTIONS.JMP and node.operands[0].mode == MODES.IMM:
        # jump to absolute (non-label) address
        print(node.operands[0])
        print(context.linkable)
        logger.fatal(f"jump to absolute address on line {node.line}. use --nolink to enable low-level functionality.", scope)

    fmt = OPCODE_FORMATS[node.opcode]

    # get register values from the operands identified via the format.
    src_operand: int = 0
    dest_operand: int = 0

    if fmt.src_operand is not None:
        src_operand = node.operands[fmt.src_operand].get_value()

    if fmt.dest_operand is not None:
        dest_operand = node.operands[fmt.dest_operand].get_value()

    immediate_value: int | None = None
    if fmt.imm_operand is not None:
        # compute immediate value, if this opcode has one.
        immediate_value = compute_immediate(node, node.operands[fmt.imm_operand], context)

    logger.verbose(f"binary: registers: {src_operand << 4 | dest_operand:08b} | {src_operand:04b} {dest_operand:04b} | {src_operand} {dest_operand}")
    logger.verbose(f"binary: opcode:    {node.opcode:08b} | 0x{node.opcode:02X}      | {fmt.mnemonic.name}")

    if immediate_value is not None:
        logger.verbose(f"binary: immediate: {immediate_value & 0xFF:08b} | {(immediate_value >> 8) & 0xFF:08b}  | 0x{immediate_value:04X}")
        logger.verbose(f"binary: result:    {src_operand << 4 | dest_operand:08b} {node.opcode:08b} {immediate_value & 0xFF:08b} {(immediate_value >> 8) & 0xFF:08b}")
    else:
        logger.verbose(f"binary: result:    {src_operand << 4 | dest_operand:08b} {node.opcode:08b}")

    result = bytearray()
    result.append((src_operand << 4) | dest_operand)  # register byte: [ssss | dddd]
    result.append(node.opcode)  # opcode byte

    if immediate_value is not None:
        result.append(immediate_value & 0xFF)  # low byte
        result.append((immediate_value >> 8) & 0xFF)  # high byte

    return result


def compute_immediate(node: InstructionNode, immediate: Operand, ctx: AssemblyContext) -> int | None:
    scope = "binary.py:compute_immediate()"
    next_pc = node.pc + node.size

    if isinstance(immediate, ImmediateOperand):
        return immediate.value  # plain constant

    if isinstance(immediate, LabelOperand):
        # only conditional branches reach here. even though we don't have PIC,
        # these will still work correctly as long as code is loaded at its org address.

        # NOTE: when PIC is added, this path will handle linkable-mode label refs,
        # emitting a pc-relative offset so the code runs correctly at any load address.
        if immediate.name not in ctx.labels:
            logger.fatal(f"undefined label \"{immediate.name}\" on line {node.line}", scope)
        label_address = ctx.labels[immediate.name]
        return (label_address - next_pc) & 0xFFFF

    # NOTE: PIC (not yet implemented).
    # [label] (REL_POINTER) and [label + reg] (OFF_POINTER) encode pc-relative offsets
    # for position-independent memory access. disabled until the linker is designed.
    if isinstance(immediate, (RelativePointerOperand, OffsetPointerOperand)):
        logger.fatal(
            f"pc-relative pointer operands ([label] / [label + reg]) are not yet supported "
            f"outside of PIC mode (line {node.line}). use a register pointer instead.",
            scope
        )

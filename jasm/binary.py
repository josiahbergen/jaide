# binary.py
# binary generation functions.
# josiah bergen, december 2025

from .language.ir.base import LabelNode, DataDirectiveNode, InstructionNode, Operand
from .language.ir.operands import ( 
    RegisterOperand, 
    PointerOperand, 
    OffsetPointerOperand, 
    ImmediateOperand, 
    RelativePointerOperand,
    LabelOperand
)
from .language.context import AssemblyContext
from .util.logger import logger
from .language.isa import INSTRUCTIONS, MODES, REGISTER_SEMANTICS, RTYPE

def generate_binary(context: AssemblyContext) -> bytearray:
    """ Generate a binary string from the IR. """
    
    binary = bytearray()
    for node in context.ir:

        old_len = len(binary)

        if isinstance(node, DataDirectiveNode):
            binary.extend(node.encode())

        elif isinstance(node, InstructionNode):
            binary.extend(encode_instruction(node, context))

        else:
            pass # label, no code to generate

        logger.debug(f"bytes: finished generating {len(binary) - old_len} bytes for {node} on line {node.line} (0x{node.pc:04X})")

    logger.debug(f"binary: generation finished ({len(binary)} bytes)")

    return binary


def encode_instruction(node: InstructionNode, context: AssemblyContext) -> bytearray:
    scope = "binary.py:encode_instruction()"

    if not context.linkable and node.mnemonic == INSTRUCTIONS.JMP and node.operands[0].mode == MODES.IMM:
        logger.fatal(f"jump to absolute address on line {node.line}. use --bios-mode to enable low-level functionality.", scope)

    bytes = bytearray()

    src_reg = 0
    dest_reg = 0
    register_positions: list[RTYPE] = REGISTER_SEMANTICS[node.mnemonic]

    # encode registers dynamically into their correct src/dest positions
    for i, op in enumerate(node.operands):
        if not isinstance(op, (RegisterOperand, PointerOperand, OffsetPointerOperand)):
            continue

        if register_positions[i] == RTYPE.SRC:
            src_reg = op.register # this operand is a source register

        elif register_positions[i] == RTYPE.DEST:
            dest_reg = op.register # this operand is a destination register

    # immediate-like operand, if any
    immediate_operand = next((op for op in node.operands 
        if op.mode in (MODES.IMM, MODES.RELATIVE, MODES.REL_POINTER, MODES.OFF_POINTER)), None)

    # get computed immediate value
    if immediate_operand is not None:
        immediate_value = compute_immediate(node, immediate_operand, context)
    else:
        immediate_value = None

    bytes.append((src_reg << 4) | dest_reg) # register byte
    bytes.append(node.opcode) # opcode byte

    logger.verbose(f"binary: instruction word: {src_reg << 4 | dest_reg:08b} | {src_reg << 4 | dest_reg} | {node.opcode:08b} | {node.opcode}")

    if immediate_value is not None:
        bytes.append(immediate_value & 0xFF) # low byte
        bytes.append((immediate_value >> 8) & 0xFF) # high byte 

    return bytes


def compute_immediate(node: InstructionNode, immediate: Operand, ctx: AssemblyContext) -> int | None:
    next_pc = node.pc + node.size

    if isinstance(immediate, ImmediateOperand):
        return immediate.value # plain old immediate constant
    
    if isinstance(immediate, LabelOperand):
        # basic relative offset (jumps, calls, etc.)
        label_address = ctx.labels[immediate.name]
        return (label_address - next_pc) & 0xFFFF # two's complement offset

    if isinstance(immediate, (RelativePointerOperand, OffsetPointerOperand)):
        # [label] i.e. pointer to relative offset
        label_address = ctx.labels[immediate.label]
        return (label_address - next_pc) & 0xFFFF # two's complement offset

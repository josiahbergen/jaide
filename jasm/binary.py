# binary.py
# binary generation functions.
# josiah bergen, december 2025

from .language.context import AssemblyContext
from .language.ir.base import AlignDirectiveNode, BreakDirectiveNode, DataDirectiveNode, InstructionNode, TimesDirectiveNode
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
            encoded = node.encode()
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

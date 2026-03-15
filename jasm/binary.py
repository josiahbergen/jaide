# binary.py
# binary generation functions.
# josiah bergen, december 2025

# lowkey gonna be a tough go

from .language.ir import IRNode, LabelNode
from .language.context import AssemblyContext
from .util.logger import logger

def generate_binary(context: AssemblyContext) -> bytearray:
    """ Generate a binary string from the IR. """
    
    binary = bytearray()
    for node in context.ir:

        if isinstance(node, LabelNode):
            # no machine code to generate!
            continue

        ml = node.get_bytes()
        binary.extend(ml)
        logger.debug(f"bytes: finished generating {len(ml)} bytes for {node} on line {node.line} (0x{node.pc:04X})")

    logger.debug(f"binary: generation finished ({len(binary)} bytes)")

    return binary

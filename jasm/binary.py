# binary.py
# binary generation functions.
# josiah bergen, december 2025

# lowkey gonna be a tough go

from .language.ir import IRNode, LabelNode
from .util.logger import logger

def generate_binary(ir: list[IRNode]) -> bytearray:
    """ Generate a binary string from the IR. """
    
    binary = bytearray()

    for node in ir:

        if isinstance(node, LabelNode):
            continue

        bits = node.get_bytes()
        logger.debug(f"bytes: generated {len(bits)} bytes for {node.short_string()} on line {node.line}")
        binary.extend(bits)

    logger.debug(f"binary: generation finished ({len(binary)} bytes)")

    return binary

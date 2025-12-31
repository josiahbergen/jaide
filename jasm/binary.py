# binary.py
# binary generation functions.
# josiah bergen, december 2025

# lowkey gonna be a tough go

from .language.ir import IRNode
from .util.logger import logger
def generate_binary(ir: list[IRNode]) -> bytearray:
    """ Generate a binary string from the IR. """
    scope = "binary.py:generate_binary()"

    logger.warning("not implemented", scope)
    return bytearray()
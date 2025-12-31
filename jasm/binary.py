# binary.py
# binary generation functions.
# josiah bergen, december 2025

# lowkey gonna be a tough go

from .language.ir import IRNode

def generate_binary(ir: list[IRNode]) -> bytearray:
    """ Generate a binary string from the IR. """

    return bytearray()
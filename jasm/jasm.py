# jasm.py
# main assembly logic and flow control.
# josiah bergen, december 2025

from jasm.util.logger import logger
from jasm.parse import generate_context
from jasm.macros import expand_macros
from jasm.labels import resolve_labels
from jasm.binary import generate_binary
from jasm.language.context import AssemblyContext


def assemble(file: str, output: str):
    """ Assemble a JASM file and return the binary. """

    logger.info("JASM assembler v0.0.4 (copyright 2026 Josiah Bergen)")
 
    # generate the IR
    ctx: AssemblyContext = generate_context(file)

    # expand macros
    expand_macros(ctx)

    # resolve labels
    resolve_labels(ctx)

    # generate binary
    binary: bytearray = generate_binary(ctx)

    # write binary to output file
    with open(output, "wb") as f:
        f.write(binary)
    logger.info(f"wrote {len(binary)} bytes to {output}.")

    logger.success("assembly complete! yay!")
    return
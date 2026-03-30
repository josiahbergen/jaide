# jasm.py
# main assembly logic and flow control.
# josiah bergen, december 2025

from jasm.binary import generate_binary
from jasm.labels import resolve_labels
from jasm.language.context import AssemblyContext
from jasm.macros import expand_macros
from jasm.parse import generate_context
from jasm.util.logger import logger


def assemble(file: str, output: str, options: dict[str, bool]):
    """Assemble a JASM file and return the binary."""

    logger.info("JASM assembler v0.0.4 (copyright 2026 Josiah Bergen)")

    # generate the IR
    ctx: AssemblyContext = generate_context(file, options)

    # expand macros
    expand_macros(ctx)

    # resolve labels
    resolve_labels(ctx)

    # generate binary
    binary: bytearray = generate_binary(ctx)

    # write binary to output file
    if ctx.write:
        f = open(output, "wb")
        _ = f.write(binary)
        logger.info(f"wrote {len(binary)} bytes to {output}.")

    logger.success("assembly complete! yay!")
    return

# jasm.py
# main assembly logic and flow control.
# josiah bergen, december 2025

from jasm.util.logger import logger
from jasm.parse import generate_ir
from jasm.macros import expand_macros
from jasm.labels import resolve_labels
from jasm.binary import generate_binary

def assemble(file: str, output: str):
    """ Assemble a JASM file and return the binary. """

    logger.info("JASM assembler v0.0.3 (copyright 2026 Josiah Bergen)")
 
    # generate the IR
    ir = generate_ir(file)

    # expand macros (to be added in a later release)
    expand_macros(ir)

    # resolve labels
    resolve_labels(ir)

    # generate binary
    binary = generate_binary(ir)

    # write binary to output file
    with open(output, "wb") as f:
        f.write(binary)
    logger.info(f"wrote {len(binary)} bytes to {output}.")

    logger.success("assembly complete! yay!")
    return
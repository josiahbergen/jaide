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
 
    # generate the IR
    ir = generate_ir(file)

    # expand macros
    ir = expand_macros(ir)

    # resolve labels
    ir = resolve_labels(ir)

    # generate binary
    binary = generate_binary(ir)

    # write binary to output file
    with open(output, "wb") as f:
        f.write(binary)
    logger.debug(f"wrote {len(binary)} bytes to {output}.")

    logger.success("assembly complete! yay!")
    return
# jasm.py
# main assembly logic and flow control.
# josiah bergen, december 2025

from jasm.binary import generate_binary
from jasm.labels import prepare_instructions
from jasm.language.context import AssemblyContext
from jasm.language.ir.base import DefineDirectiveNode, MacroDefinitionNode, OrgDirectiveNode
from jasm.macros import expand_macros
from jasm.parse import generate_context, parse_text
from jasm.util.logger import logger


def assemble_string(source: str, options: dict[str, bool] = {}) -> bytes:
    """Assemble JASM source from a string and return the binary bytes.

    No file I/O or import directive support — use assemble() for those.
    Reuses the cached Lark parser, so repeated calls are fast (~0.2 ms each).
    """
    fake = "<string>.jasm"
    ir_nodes = parse_text(source, fake)

    ctx = AssemblyContext(fake, options)
    for node in ir_nodes:
        if isinstance(node, MacroDefinitionNode):
            ctx.add_macro(node.name, node)
        elif isinstance(node, DefineDirectiveNode):
            ctx.add_constant(node.name, node.value)
        elif isinstance(node, OrgDirectiveNode):
            ctx.set_origin(node.address)
        else:
            ctx.ir.append(node)

    expand_macros(ctx)
    prepare_instructions(ctx)
    return bytes(generate_binary(ctx))


def assemble(file: str, output: str, options: dict[str, bool] = {}):
    """Assemble a JASM file and return the binary."""

    logger.info("JASM assembler v0.0.5 (copyright 2026 Josiah Bergen)")

    # generate the IR using a recursive parser + transformer
    # includes macros, labels, constants, and directives
    ctx: AssemblyContext = generate_context(file, options)

    # we get the ir in the form of a big list of nodes.
    # we need to expand macros into the actual nodes that will be encoded.
    # this step needs to be done before we can prepare instructions for encoding.
    expand_macros(ctx)

    # ir is now as if there were never any macros or imports.
    # this step gives all nodes a pc value, and converts label operands to absolute immediates.
    # it also does a few other things that need to be done before we can generate the binary.
    prepare_instructions(ctx)

    # generate binary
    binary: bytearray = generate_binary(ctx)

    # write binary to output file
    if ctx.write:
        f = open(output, "wb")
        _ = f.write(binary)
        logger.info(f"wrote {len(binary)} bytes to {output}.")

    logger.success("assembly complete! yay!")
    return

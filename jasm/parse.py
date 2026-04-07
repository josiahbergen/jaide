# parse.py
# parsing functions for the JASM language.
# josiah bergen, december 2025

import os

from lark import Lark

from .language.context import AssemblyContext
from .language.grammar import GRAMMAR
from .language.transformer import IRTransformer
from .language.ir.base import (
    ImportDirectiveNode,
    IRNode,
    MacroDefinitionNode,
    MacroCallNode,
    InstructionNode,
    DefineDirectiveNode,
    OrgDirectiveNode,
)
from .util.logger import logger


def generate_context(file: str, options: dict[str, bool]) -> AssemblyContext:
    """Generate the context from the source file."""

    # dictionary of lists of IR nodes, one for each file that is parsed
    ir: dict[str, list[IRNode]] = {}

    # recursive function to parse all files
    parse_file(file, ir)

    logger.debug("parse: transformer finished!")
    logger.debug(f"parse: flattening {len(ir)} file{'s' if len(ir) > 1 else ''}...")

    first_file = list[str](ir.keys())[0] # root file, so the recursive parsing mimics the original file order
    context: AssemblyContext = AssemblyContext(first_file)

    # recursively generate context from all parsed files
    update_context_from_file(context, ir, first_file)

    logger.debug(f"parse: done! generated {len(context.ir)} nodes.")

    logger.verbose("parse: all nodes:")
    for node in context.ir:
        logger.verbose(f"parse: {str(node)}")

    logger.debug(f"context: added {len(context.constants)} constant{'' if len(context.constants) == 1 else 's'}.")
    logger.debug(f"context: added {len(context.macros)} macro definition{'' if len(context.macros) == 1 else 's'}.")
    logger.debug(f"context: used data from {len(context.files)} file{'' if len(context.files) == 1 else 's'}.")
    logger.debug(f"context: origin: {context.origin if context.origin != -1 else 'not set'}")
    logger.debug(f"context: linkable: {context.linkable}")
    logger.debug(f"context: write: {context.write}")

    return context


def check_file(file: str) -> None:
    """Check if a file is a valid JASM file."""
    scope = "parse.py:check_file()"

    logger.verbose(f"parse: checking file {file}...")

    if not os.path.exists(file):
        logger.fatal(f'file "{file}" does not exist', scope)

    if not file.endswith(".jasm"):
        logger.warning(f"file {file} does not look like a JASM file", scope)


def parse_file(file: str, ir: dict[str, list[IRNode]]) -> None:
    """Parse a file and return all IR nodes for all imports."""
    scope = "parse.py:parse_file()"

    # check if file is valid
    file = os.path.normcase(os.path.realpath(file))
    check_file(file)

    # open and read the file
    try:
        with open(file, "r") as f:
            text = f.read()
    except Exception as e:
        logger.fatal(f"error reading file {file}: {e}. perhaps you have a bad import path?", scope)

    # parse the text
    try:
        parser = Lark(GRAMMAR, parser="lalr")
        tree = parser.parse(text)
    except Exception as e:
        logger.fatal(f"parser error in file {file}: {e}", scope)

    # generate the IR
    ir_nodes: list[IRNode] = IRTransformer(source_file=file).transform(tree)
    ir[file] = ir_nodes

    # find all import nodes
    imports = [node for node in ir[file] if isinstance(node, ImportDirectiveNode)]
    if len(imports) > 0:
        logger.debug(f"parse: found {len(imports)} import file(s): {', '.join([import_node.filename for import_node in imports])}")

    for import_node in imports:
        if import_node.import_path in ir:
            # skip if already parsed
            logger.warning(f"circular or double import detected: {import_node.filename} already parsed, skipping...", scope)
            continue

        # recursively parse import files
        parse_file(import_node.import_path, ir)
    return


def update_context_from_file(context: AssemblyContext, ir: dict[str, list[IRNode]], file: str) -> None:
    """Recursive function to flatten imports such that they keep their original order. Also adds any directives to the assembly context."""

    for node in ir[file]:
        if isinstance(node, ImportDirectiveNode):
            if node.import_path in context.files:
                # skip if already added
                continue

            logger.debug(f"parse: adding {node.import_path} to main list at index {len(context.ir)}")
            context.files.add(node.import_path)

            # found import, recursively update the context
            update_context_from_file(context, ir, node.import_path)

        elif isinstance(node, MacroDefinitionNode):
            logger.debug(f"parse: adding macro definition {node.name} to assembly context")
            context.add_macro(node.name, node)

        elif isinstance(node, DefineDirectiveNode):
            logger.debug(f"parse: adding define directive {node.name} to assembly context")
            context.add_constant(node.name, node.value)

        elif isinstance(node, OrgDirectiveNode):
            logger.debug(f"parse: adding org directive {node.address} to assembly context")
            context.set_origin(node.address)

        else:
            # not a directive or macro definition, so add to the big list
            context.ir.append(node)
    return

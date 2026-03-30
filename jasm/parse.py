# parse.py
# parsing functions for the JASM language.
# josiah bergen, december 2025

import os

from lark import Lark

from .language.context import AssemblyContext
from .language.grammar import GRAMMAR
from .language.transformer import IRTransformer
from .language.ir.base import ImportDirectiveNode, IRNode, MacroDefinitionNode
from .util.logger import logger


def generate_context(file: str, options: dict[str, bool]) -> AssemblyContext:
    """Generate the context from the source file."""

    # dictionary of lists of IR nodes, one for each file that is parsed
    context = AssemblyContext(file, options)
    ir: dict[str, list[IRNode]] = {}

    # recursive function to parse all files
    parse_file(file, ir)

    # flatten the IR and return
    context.ir = flatten_imports(context, ir)
    logger.debug(f"parse: done! generated {len(context.ir)} nodes.")

    logger.verbose("parse: all nodes:")
    for node in context.ir:
        logger.verbose(f"parse: {str(node)}")

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
    ir_nodes: list[IRNode] = IRTransformer().transform(tree)
    ir[file] = ir_nodes

    # find all import nodes
    imports = [node for node in ir[file] if isinstance(node, ImportDirectiveNode)]
    if len(imports) > 0:
        logger.debug(f"parse: found {len(imports)} import file(s): {', '.join([import_node.filename for import_node in imports])}")

    for import_node in imports:
        if import_node.filename in ir:
            # skip if already parsed
            logger.warning(f"circular or double import detected: {import_node.filename} already parsed, skipping...", scope)
            continue

        # recursively parse import files
        parse_file(import_node.filename, ir)
    return


def flatten_imports(context: AssemblyContext, ir: dict[str, list[IRNode]]) -> list[IRNode]:
    """Flatten the main ir dict into a single list of linear IR nodes."""

    logger.debug(f"parse: flattening {len(ir)} file{'s' if len(ir) > 1 else ''}...")
    big_list = []
    added_files: set[str] = set[str]()
    append_ir_nodes(context, list[str](ir.keys())[0], ir, big_list, added_files)
    return big_list


def append_ir_nodes(
    context: AssemblyContext, file: str, ir: dict[str, list[IRNode]], big_list: list[IRNode], added_files: set[str]) -> None:
    """Recursive function to flatten imports such that they keep their original order. Also adds macro definitions to the assembly context."""

    for node in ir[file]:
        if isinstance(node, ImportDirectiveNode):
            if node.filename in added_files:
                # skip if already added
                continue

            logger.debug(f"parse: adding {node.filename} to main list at index {len(big_list)}")
            added_files.add(node.filename)
            append_ir_nodes(context, node.filename, ir, big_list, added_files)

        elif isinstance(node, MacroDefinitionNode):
            logger.debug(f"parse: adding macro definition {node.name} to assembly context")
            context.add_macro(node.name, node)
            # don't need to add macro defs to the ir, they're already saved

        else:
            big_list.append(node)
    return

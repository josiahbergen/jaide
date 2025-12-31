# parse.py
# parsing functions for the JASM language.
# josiah bergen, december 2025

from lark.lexer import Token
from lark.tree import Tree
import os
from .language.ir import IRNode, InstructionNode, OperandNode, ImportDirectiveNode, DataDirectiveNode, LabelNode
from .util.logger import logger
from .language.grammar import GRAMMAR
from lark import Lark, ParseTree

def generate_ir(file: str) -> list[IRNode]:
    """ Generate the IR from the source file. """

    # dictionary of lists of IR nodes, one for each file that is parsed
    ir: dict[str, list[IRNode]] = {}

    # recursive function to parse all files
    parse_file(file, ir)

    # flatten the IR and return
    ir_nodes = flatten_imports(ir)
    logger.debug(f"parse: done! generated {len(ir_nodes)} nodes.")

    for node in ir_nodes:
        logger.verbose(f"parse: node: {str(node)}")

    return ir_nodes


def check_file(file: str) -> None:
    """ Check if a file is a valid JASM file. """
    scope = "parse.py:check_file()"

    logger.verbose(f"parse: checking file {file} (type: {type(file).__name__})...")

    if not os.path.exists(file):
        logger.fatal(f"imported file {file} does not exist", scope)

    if not file.endswith(".jasm"):
        logger.warning(f"imported file {file} does not look like a JASM file", scope)


def parse_file(file: str, ir: dict[str, list[IRNode]]) -> None:
    """ Parse a file and return all IR nodes for all imports. """
    scope = "parse.py:parse_file()"

    # check if file is valid
    check_file(file)

    # open and read the file
    try:
        with open(file, "r") as f:
            text = f.read()
    except Exception as e:
        logger.fatal(f"error reading file {file}: {e}. perhaps you have a bad import path?", scope)
    
    # parse the text
    try:
        parser = Lark(GRAMMAR, parser='lalr')
        tree = parser.parse(text)
    except Exception as e:
        logger.fatal(f"parser error in file {file}: {e}", scope)
    
    # generate the IR
    ir_nodes = generate_ir_nodes(tree)
    ir[file] = ir_nodes

    # find all import nodes
    imports = [node for node in ir[file] if isinstance(node, ImportDirectiveNode)]
    logger.debug(f"parse: found {len(imports)} import file(s): {", ".join([import_node.filename for import_node in imports])}")

    for import_node in imports:
        
        # skip if already parsed
        if import_node.filename in ir:
            logger.warning(f"circular or double import detected: {import_node.filename} already parsed, skipping...", scope)
            continue
        
        # recursively parse the import file
        parse_file(import_node.filename, ir)
    return


def generate_ir_nodes(tree: ParseTree) -> list[IRNode]:
    scope = "parse.py:generate_ir_nodes()"
    ir_nodes = []

    for subtree in tree.children:
        logger.verbose(f"parse: processing {type(subtree)}: {str(subtree)}")

        # Skip Token objects (they don't have .data attribute)
        if isinstance(subtree, Token):
            if subtree.type == "COMMENT":
                logger.debug(f"parse: skipping comment: \"{str(subtree)}\"")
                continue
            logger.warning(f"skipping possibly important token: \"{str(subtree)}\" (type: {subtree.type})", scope)
            continue

        # Only Tree objects have .data attribute
        if not isinstance(subtree, Tree):
            logger.warning(f"skipping unexpected node type: {type(subtree)}", scope)
            continue

        node_type = subtree.data # this is any of: instruction, directive, label, macro, data, macro_call
        node_children = len(subtree.children)
        logger.verbose(f"parse: parsing info for {node_type} with {node_children} children")

        match node_type:
            case "instruction":
                mnemonic = next(subtree.find_token("MNEMONIC"))
                operand_list = next(subtree.find_data("operand_list"), None)
                operands = operand_list.children if operand_list else []
                line = warn_if_no_line(mnemonic, scope)
                
                # fatal if we find non-token operands (for an instruction, at least)
                if not all(isinstance(op, Token) for op in operands):
                    logger.fatal(f"found non-token operands for instruction {mnemonic.value} on line {line}", scope)
        
                opstring = "operands "+ ", ".join([str(op) for op in operands]) if operands else "no operands"
                logger.debug(f"parse: creating node for instr {mnemonic.value} with {opstring} (line {line})")

                operand_nodes = [OperandNode(line, op.type, op.value) for op in operands if isinstance(op, Token)]
                ir_nodes.append(InstructionNode(line, mnemonic.value, operand_nodes))

            case "label":
                label = next(subtree.find_token("LABELNAME"))
                line = warn_if_no_line(label, scope)

                logger.debug(f"parse: creating node for label \"{label.value}\" (line {line})")
                ir_nodes.append(LabelNode(line, label.value))

            case "directive":
                import_directive = next(subtree.find_data("import_directive"), None)
                data_directive = next(subtree.find_data("data_directive"), None)
                logger.verbose("parse: parsing directive type...")
                logger.verbose(f"parse: tried import directive: {str(import_directive)}")
                logger.verbose(f"parse: tried data directive: {str(data_directive)}")

                if import_directive:
                    logger.debug("parse: creating node for import directive...")
                    string = next(import_directive.find_token("STRING"))
                    line = warn_if_no_line(string, scope)
                    ir_nodes.append(ImportDirectiveNode(line, string.value))

                elif data_directive:
                    logger.debug("parse: creating node for data directive...")
                    line = warn_if_no_line(next(data_directive.find_token("DATA")), scope)
                    data = list[Token](data_directive.scan_values(lambda v: isinstance(v, Token) and v.type in {"NUMBER", "STRING"}))
                    ir_nodes.append(DataDirectiveNode(line, [(token.type, token.value) for token in data]))
                
                else:
                    logger.fatal(f"unknown directive: {str(subtree)}", scope)
            
            case _:
                logger.fatal(f"unknown node type: {node_type}", scope)
    
    return ir_nodes


def flatten_imports(ir: dict[str, list[IRNode]]) -> list[IRNode]:
    """ Flatten the main ir dict into a single list of linear IR nodes. """

    logger.debug(f"parse: flattening {len(ir)} file{"s" if len(ir) > 1 else ""}...")
    big_list = []
    added_files: set[str] = set[str]()
    append_ir_nodes(list[str](ir.keys())[0], ir, big_list, added_files)
    return big_list

def append_ir_nodes(file: str, ir: dict[str, list[IRNode]], big_list: list[IRNode], added_files: set[str]) -> None:
    """ Recursive function to flatten imports such that they keep their original order. """
    
    for node in ir[file]:
        if isinstance(node, ImportDirectiveNode):
            if node.filename in added_files:
                # skip if already added
                continue

            logger.verbose(f"parse: adding {node.filename} to main list at index {len(big_list)}")
            added_files.add(node.filename)
            append_ir_nodes(node.filename, ir, big_list, added_files)
        else:
            big_list.append(node)
    

def warn_if_no_line(node: Token, scope: str) -> int:
    """ Warn if the node has no line number, and return 0 if so. """
    if not node.line:
        logger.warning(f"no line number found for {type(node).__name__}: {node.value}", scope)
        return 0
    return node.line
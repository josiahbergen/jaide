# macros.py
# macros resolution functions.
# josiah bergen, december 2025

from .language.ir import IRNode, MacroNode, MacroCallNode
from .util.logger import logger
# planned eventually. gonna get the whole thing working first before i deal with this.

def expand_macros(ir: list[IRNode]) -> list[IRNode]:
    """ Parse and expand macros in the IR. """

    # iterate backwards to avoid index shifting when modifying the list
    for i in range(len(ir) - 1, -1, -1):
        node = ir[i]

        if isinstance(node, MacroCallNode):
            logger.debug(f"macros: expanding macro call {node.name} on line {node.line}")

            if node.name in IRNode.macros:
                
                macro = IRNode.macros[node.name]
                logger.verbose(f"macros: expanding macro {node.name} on line {node.line} with {len(macro.args)} arguments")
                expanded = macro.expand(node.args)

                # Replace the macro call node with the expanded nodes
                ir.pop(i)
                ir[i:i] = expanded
                
                logger.verbose(f"macros: expanded macro {node.name} on line {node.line} into {len(expanded)} nodes at index {i}")

    logger.debug(f"macros: expanded {len(ir)} nodes.")
    for node in ir:
        logger.verbose(f"completed expansion: {str(node)}")
    return ir

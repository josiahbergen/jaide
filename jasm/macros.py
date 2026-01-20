# macros.py
# macros resolution functions.
# josiah bergen, december 2025

from .language.ir import IRNode, InstructionNode, MacroCallNode
from .util.logger import logger
# planned eventually. gonna get the whole thing working first before i deal with this.

def expand_macros(ir: list[IRNode]) -> None:
    """ Parse and expand macros in the IR. """

    # iterate backwards to avoid index shifting when modifying the list
    # we only make the list longer (not shorter), so we can iterate backwards
    for i in range(len(ir) - 1, -1, -1):
        node = ir[i]

        if isinstance(node, MacroCallNode):
            logger.debug(f"macros: expanding macro call {node.name} on line {node.line}")

            if node.name in IRNode.macros:
                
                macro = IRNode.macros[node.name]
                logger.verbose(f"macros: expanding macro {node.name} on line {node.line} with {len(macro.args)} arguments")
                expanded = macro.expand(node.args)
                ir.pop(i)

                # this inserts a list of items at some index
                # strange syntax but it works
                ir[i:i] = expanded 
                
                logger.verbose(f"macros: expanded macro {node.name} on line {node.line} into {len(expanded)} nodes at index {i}")

    logger.debug(f"macros: expanded {len(ir)} nodes.")
    for node in ir:
        if isinstance(node, InstructionNode):
            logger.verbose(f"completed expansion: {node.short_string()} {", ".join([str(op) for op in node.operands])}")
        else:
            logger.verbose(f"completed expansion: {node}")
    return

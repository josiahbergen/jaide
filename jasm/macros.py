# macros.py
# macros resolution functions.
# josiah bergen, december 2025

from .language.ir import IRNode, InstructionNode, MacroCallNode
from .util.logger import logger
from .language.context import AssemblyContext

def expand_macros(context: AssemblyContext) -> None:
    """ Parse and expand macros in the IR. """

    # iterate backwards to avoid index shifting when modifying the list
    # we only make the list longer (not shorter), so we can iterate backwards
    
    logger.warning("macros: expansion not yet implemented", "macros.py:expand_macros()")
    
    # for i in range(len(context.ir) - 1, -1, -1):
    #     node = context.ir[i]

    #     if isinstance(node, MacroCallNode):
    #         logger.debug(f"macros: expanding macro call {node.name} on line {node.line}")

    #         if node.name in context.macros:
                
    #             macro = context.macros[node.name]
    #             logger.verbose(f"macros: expanding macro {node.name} on line {node.line} with {len(macro.args)} arguments")
    #             expanded = macro.expand(node.args, line=node.line)
    #             context.ir.pop(i)

    #             # this inserts a list of items at some index
    #             # strange syntax but it works
    #             context.ir[i:i] = expanded 
                
    #             logger.verbose(f"macros: expanded macro {node.name} on line {node.line} into {len(expanded)} nodes at index {i}")

    # logger.debug(f"macros: expanded {len(context.ir)} nodes.")
    # for node in context.ir:
    #     if isinstance(node, InstructionNode):
    #         logger.verbose(f"completed expansion: {node} {", ".join([str(op) for op in node.operands])}")
    #         # node.addressing_mode = node.get_addressing_mode()
    #         node.size = node.get_size()
    #     else:
    #         logger.verbose(f"completed expansion: {node}")
    # return

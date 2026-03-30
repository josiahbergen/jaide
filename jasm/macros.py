# macros.py
# macros resolution functions.
# josiah bergen, december 2025

from .language.context import AssemblyContext
from .language.ir.base import IRNode, MacroCallNode, MacroDefinitionNode
from .util.logger import logger


def expand_macros(context: AssemblyContext) -> None:
    """Parse and expand macros in the IR."""

    i: int = 0
    while i < len(context.ir):
        # walk the ir
        node: IRNode = context.ir[i]

        if not isinstance(node, MacroCallNode):
            i += 1  # not a macro call
            continue

        if node.name not in context.macros:
            logger.fatal(
                f"definition for macro {node.name} not found! (line {node.line})",
                "macros.py:expand_macros()",
            )

        call: MacroCallNode = node
        definition: MacroDefinitionNode = context.macros[node.name]
        logger.verbose(
            f"macro: expanding macro {node.name} on line {node.line} with {len(call.args)} arguments"
        )

        expanded = definition.expand(call.args, node.line)
        _ = context.ir.pop(i)

        # this inserts a list of items at some index
        # strange syntax but it works
        context.ir[i:i] = expanded

        logger.verbose(
            f"macro: expanded macro {node.name} on line {node.line} into {len(expanded)} nodes at index {i}"
        )
        i += (
            len(expanded) - 1
        )  # we removed the original call node, and added the expanded nodes

    logger.debug(f"macro: expanded {len(context.ir)} nodes.")
    for node in context.ir:
        logger.verbose(f"completed expansion: {node}")

# labels.py
# label resolution functions.
# josiah bergen, december 2025

from .language.ir.base import LabelNode, InstructionNode
from .language.ir.operands import ImmediateOperand, LabelOperand
from .language.ir.terminals import NumberTerminal
from .util.logger import logger
from .language.context import AssemblyContext

def resolve_labels(context: AssemblyContext) -> None:
    """ Resolve labels in the IR. """
    scope = "labels.py:resolve_labels()"
    
    logger.debug("labels: resolving labels and constants...")
    pc = context.origin or 0  # defaults to 0 if not set

    for node in context.ir:

        # we actually set the pc for all nodes, not just labels.
        # at this point, the only nodes that are left are instructions, data/times directives, and labels.
        node.pc = pc 

        if isinstance(node, LabelNode):

            if node.name in context.labels.keys():
                logger.fatal(f"label \"{node.name.lower()}\" defined multiple times (line {node.line})", scope)

            if node.name in context.constants.keys():
                logger.fatal(f"label \"{node.name.lower()}\" already defined as a constant (line {node.line})", scope)

            logger.debug(f"labels: \"{node.name}\" defined at PC {pc}")
            context.labels[node.name] = pc
            continue

        # resolve constants, parser emits them as labels
        if isinstance(node, InstructionNode):
            for i, operand in enumerate(node.operands):
                if isinstance(operand, LabelOperand) and operand.name in context.constants:
                    logger.debug(f"labels: populating constant  operand {operand} -> {context.constants[operand.name]} on line {node.line}")
                    
                    # swap out the label for a convenient immediate
                    node.operands[i] = ImmediateOperand(operand.line, NumberTerminal(operand.line, str(context.constants[operand.name])))

        size = node.get_size()  # size in words

        if isinstance(node, InstructionNode):
            # because we are done macro expansion, we can finally do this
            node.opcode = node.get_opcode()
            node.size = size

        # increment pc!
        logger.verbose(f"labels: pc {pc} -> {pc + size}")
        pc += size

    logger.debug(f"labels: resolved {len(context.labels)} labels.")
    return

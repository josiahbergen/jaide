# labels.py
# label resolution functions.
# josiah bergen, december 2025

from .language.ir.base import LabelNode, InstructionNode
from .util.logger import logger
from .language.context import AssemblyContext

def resolve_labels(context: AssemblyContext) -> None:
    """ Resolve labels in the IR. """
    scope = "labels.py:resolve_labels()"
    
    logger.debug("labels: resolving labels...")
    pc = context.origin  # defaults to 0, but can be overridden by the caller

    for node in context.ir:

        # we actually set the pc for all nodes, not just labels.
        # at this point, the only nodes that are left are instructions, data directives, and labels.
        node.pc = pc 

        if isinstance(node, LabelNode):
            label_name = node.name.lower()

            if label_name in context.labels.keys():
                logger.fatal(f"label \"{label_name}\" defined multiple times (line {node.line})", scope)

            logger.debug(f"labels: \"{label_name}\" defined at PC {pc}")
            context.labels[label_name] = pc
            continue
        
        size = node.get_size() # size in words

        if isinstance(node, InstructionNode):
            # because we are done macro expansion, we can get this 
            # out of the way during this pass!
            node.opcode = node.get_opcode()
            node.size = size

        # increment pc!
        logger.verbose(f"labels: pc {pc} -> {pc + size}")
        pc += size

    logger.debug(f"labels: resolved {len(context.labels)} labels.")
    return

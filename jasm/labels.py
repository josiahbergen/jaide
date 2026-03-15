# labels.py
# label resolution functions.
# josiah bergen, december 2025

from .language.ir import IRNode, LabelNode
from .util.logger import logger
from .language.context import AssemblyContext

def resolve_labels(context: AssemblyContext) -> None:
    """ Resolve labels in the IR. """
    scope = "labels.py:resolve_labels()"
    
    # this should be as simple as importing and optimizing the functions from old/instructions.py 

    logger.debug("labels: resolving labels...")
    pc = context.origin  # defaults to 0, but can be overridden by the caller

    for node in context.ir:

        # we actually set the pc for all nodes, not just labels,
        # but the pc is only incremented for non-label nodes.
        # the rest of this logic is just for error checking and logging.
        node.pc = pc 

        if isinstance(node, LabelNode):
            label_name = node.name.lower()

            if label_name in context.labels.keys():
                logger.fatal(f"label \"{label_name}\" defined multiple times (line {node.line})", scope)

            logger.debug(f"labels: \"{label_name}\" defined at PC {pc}")
            context.labels[label_name] = pc
            continue

        # not a label, so increment PC
        size = node.get_size()
        logger.verbose(f"labels: pc {pc} -> {pc + size}")
        pc += size

    logger.debug(f"labels: resolved {len(context.labels)} labels.")
    return

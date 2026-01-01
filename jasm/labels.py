# labels.py
# label resolution functions.
# josiah bergen, december 2025

from .language.ir import IRNode, LabelNode
from .util.logger import logger

def resolve_labels(ir: list[IRNode]) -> None:
    """ Resolve labels in the IR. """
    scope = "labels.py:resolve_labels()"
    
    # this should be as simple as importing and optimizing the functions from old/instructions.py 

    logger.debug("labels: resolving labels...")
    pc = 0

    for node in ir:

        # we actually set the pc for all nodes, not just labels,
        # but the pc is only incremented for non-label nodes.
        # the rest of this logic is just for error checking and logging.
        node.pc = pc 

        if isinstance(node, LabelNode):
            label_name = node.label.lower()

            if label_name in IRNode.labels.keys():
                logger.fatal(f"label \"{label_name}\" defined multiple times (line {node.line})", scope)

            logger.debug(f"labels: \"{label_name}\" defined at PC {pc}")
            IRNode.labels[label_name] = pc
            continue

        # not a label, so increment PC
        size = node.get_size()
        logger.verbose(f"labels: pc {pc} -> {pc + size}")
        pc += size

    logger.debug(f"labels: resolved {len(IRNode.labels)} labels.")
    return

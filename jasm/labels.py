# labels.py
# label resolution functions.
# josiah bergen, december 2025

from .language.ir import IRNode
from .util.logger import logger

def resolve_labels(ir: list[IRNode]) -> list[IRNode]:
    """ Resolve labels in the IR. """
    scope = "labels.py:resolve_labels()"
    
    # this should be as simple as importing and optimizing the functions from old/instructions.py 
    logger.warning("not implemented", scope)
    return ir
# macros.py
# macros resolution functions.
# josiah bergen, december 2025

from .language.ir import IRNode
from .util.logger import logger
# planned eventually. gonna get the whole thing working first before i deal with this.

def expand_macros(ir: list[IRNode]) -> list[IRNode]:
    """ Parse and expand macros in the IR. """

    logger.warning("macros are not yet supported: skipping expansion.", "macros.py:expand_macros()")
    return ir

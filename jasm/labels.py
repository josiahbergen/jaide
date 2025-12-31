# labels.py
# label resolution functions.
# josiah bergen, december 2025

from .language.ir import IRNode

def resolve_labels(ir: list[IRNode]) -> list[IRNode]:
    """ Resolve labels in the IR. """
    
    # this should be as simple as importing and optimizing the functions from old/instructions.py 
    return ir
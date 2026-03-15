# context.py
# holds assembly context information.
# josiah bergen, march 2026

from .ir import MacroDefinitionNode, IRNode
from ..util.logger import logger

class AssemblyContext:

    def __init__(self, file: str, origin: int = 0):

        self.file: str = file                              # current file
        self.ir: list[IRNode] = []                         # IR
        self.labels: dict[str, int] = {}                   # labels
        self.macros: dict[str, MacroDefinitionNode] = {}   # macros
        self.origin: int = origin                          # starting PC

    def add_label(self, label: str, pc: int) -> None:
        scope = "context.py:AssemblyContext.add_label()"
        label = label.lower().strip()

        if label in self.labels.keys():
            logger.fatal(f"label \"{label}\" defined multiple times! note that labels are case-insensitive.", scope)

        logger.debug(f"context: label \"{label}\" defined at PC {pc}")
        self.labels[label] = pc

    def add_macro(self, name: str, macro: MacroDefinitionNode) -> None:
        scope = "context.py:AssemblyContext.add_macro()"
        name = name.lower().strip()

        if name in self.macros.keys():
            logger.warning(f"macro \"{name}\" re-defined! note that macro names are case-insensitive.", scope)
        
        self.macros[name] = macro

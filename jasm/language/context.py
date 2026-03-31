# context.py
# holds assembly context information.
# josiah bergen, march 2026

from ..util.logger import logger
from .ir.base import MacroDefinitionNode


class AssemblyContext:
    def __init__(self, root_file: str, options: dict[str, bool] | None = None):
        from .ir.base import IRNode, MacroDefinitionNode

        self.root: str = root_file  # current file
        self.ir: list[IRNode] = []  # IR
        self.labels: dict[str, int] = {}  # labels
        self.constants: dict[str, int] = {}  # constants
        self.macros: dict[str, MacroDefinitionNode] = {}  # macros
        self.origin: int | None = None  # starting pc

        self.files: set[str] = set[str]() # all files that contributed to the binary
        self.files.add(self.root)

        # optional behavior changes (more to come, hopefully)
        self.linkable: bool = options.get("linkable", True) if options else True  # linkable mode
        self.write: bool = options.get("write", True) if options else True  # write mode

    def add_label(self, label: str, pc: int) -> None:
        scope = "context.py:AssemblyContext.add_label()"
        label = label.lower().strip()

        if label in self.labels.keys():
            logger.fatal(f'label "{label}" defined multiple times! note that labels are case-insensitive.', scope)

        logger.debug(f'context: label "{label}" defined at PC {pc}')
        self.labels[label] = pc

    def add_macro(self, name: str, macro: MacroDefinitionNode) -> None:

        scope = "context.py:AssemblyContext.add_macro()"
        name = name.upper().strip()

        if name in self.macros.keys():
            logger.warning(f'macro "{name}" re-defined! note that macro names are case-insensitive.', scope)

        self.macros[name] = macro

    def add_constant(self, name: str, value: int) -> None:
        scope = "context.py:AssemblyContext.add_constant()"
        name = name.upper().strip()

        if name in self.constants.keys():
            logger.warning(f'constant "{name}" re-defined! note that constant names are case-insensitive.', scope)

        self.constants[name] = value


    def set_origin(self, address: int) -> None:
        scope = "context.py:AssemblyContext.set_origin()"
        if address < 0:
            logger.fatal(f"origin address {address} is negative! must be a positive 16-bit value.", scope)
        if self.origin is not None:
            logger.warning(f"origin address {address} set multiple times!", scope)
        
        self.origin = address
        return
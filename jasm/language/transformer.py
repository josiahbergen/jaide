# transformer.py
# jasm transformer
# josiah bergen, march 2026


from lark import Transformer, v_args, Token


from ..util.logger import logger

from .ir.base import (
    IRNode,
    Operand,
    InstructionNode, 
    LabelNode,
    DataDirectiveNode,
    ImportDirectiveNode,
    OrgDirectiveNode,
    DefineDirectiveNode,
    TimesDirectiveNode,
    AlignDirectiveNode,
    MacroDefinitionNode,
    MacroCallNode,
)
from .ir.operands import (
    LabelOperand,
    ImmediateOperand,
    RegisterOperand,
    PointerOperand,
    OffsetPointerOperand,
    RelativePointerOperand,
    MacroArgumentOperand,
)
from .ir.terminals import (
    IdentifierTerminal, 
    StringTerminal, 
    NumberTerminal,
    RegisterTerminal,
    MnemonicTerminal,
)


def line(item: Token | IRNode) -> int:
    # dynamically get the line number from a token or IRNode. useful.
    return item.line or 0 if isinstance(item, Token) else item.line


def assert_operand_count(operands: tuple[Operand, ...], expected: int, scope: str):
    if len(operands) != expected:
        logger.fatal(f"transformer: {scope} must have {expected} operands", scope)
    return


@v_args(inline=True)  # arguments are inlined into the function as *args
class IRTransformer(Transformer):

    def __init__(self, source_file: str):
        super().__init__()
        self.filename: str = source_file

    def start(self, *statements):
        # base level node, return the entire transformed tree.
        # we return a list because generate_ir_nodes() must return a list[IRNode].
        return [s for s in statements if s is not None]

    # instructions

    def instruction(self, mnemonic: MnemonicTerminal, operands: list[Operand] = []):
        return InstructionNode(line(mnemonic), self.filename, mnemonic.value, operands)

    def operand_list(self, *operands: Operand):
        if len(operands) == 0:
            return []
        return list[Operand](operands)

 

    def operand(self, terminal: IdentifierTerminal | NumberTerminal | RegisterTerminal):
        # basic terminal operands
        operand_map = {
            IdentifierTerminal: LabelOperand,
            NumberTerminal: ImmediateOperand,
            RegisterTerminal: RegisterOperand,
        }
        return operand_map[type(terminal)](line(terminal), self.filename, terminal)

    def pointer_operand(self, register: RegisterTerminal):
        # "[" REGISTER "]"
        return PointerOperand(line(register), self.filename, register)

    def offset_pointer_operand(self, identifier: IdentifierTerminal, register: RegisterTerminal):
        # "[" IDENTIFIER "+" REGISTER "]"
        return OffsetPointerOperand(line(identifier), self.filename, identifier, register)

    def relative_pointer_operand(self, identifier: IdentifierTerminal):
        # "[" IDENTIFIER "]"
        return RelativePointerOperand(line(identifier), self.filename, identifier)

    def macro_arg(self, identifier: IdentifierTerminal):
        # "%" IDENTIFIER
        return MacroArgumentOperand(line(identifier), self.filename, identifier)

    def expression(self, *_operands):
        logger.fatal("transformer: expressions are not yet implemented.", "transformer.py:expression()")

    # directives

    def directive(self, directive: DataDirectiveNode | ImportDirectiveNode):
        # receives an already parsed DataDirectiveNode or ImportDirectiveNode,
        # so just return it.
        return directive

    def import_directive(self, _import: Token, string: StringTerminal):
        # "IMPORT" STRING
        return ImportDirectiveNode(line(string), self.filename, string.value)

    def org_directive(self, _org: Token, address: NumberTerminal):
        # "ORG" NUMBER
        return OrgDirectiveNode(line(address), self.filename, address.value)

    def define_directive(self, _define: Token, name: IdentifierTerminal, value: NumberTerminal):
        # "DEFINE" IDENTIFIER NUMBER
        return DefineDirectiveNode(line(name), self.filename, name.value, value.value)

    def times_directive(self, _times: Token, count: NumberTerminal, value: NumberTerminal):
        # "TIMES" NUMBER NUMBER
        return TimesDirectiveNode(line(count), self.filename, count.value, value.value)

    def align_directive(self, _align: Token, alignment: NumberTerminal):
        # "ALIGN" NUMBER
        return AlignDirectiveNode(line(alignment), self.filename, alignment.value)

    def data_directive(self, _data: Token, *constants: NumberTerminal | StringTerminal):
        # we get a bunch of terminals, and gotta convert/annotate them into a list
        # of tuples of (Type, str) that the DataDirectiveNode expects.
        items: list[tuple[DataDirectiveNode.Type, str]] = []
        for constant in constants:
            if isinstance(constant, NumberTerminal):
                items.append((DataDirectiveNode.Type.NUMBER, constant.value))
            else: # StringTerminal
                items.append((DataDirectiveNode.Type.STRING, constant.value))
        
        # return parsed information!
        return DataDirectiveNode(line(_data), self.filename, items)

    # macros

    def macro_definition(self, _macro: Token, name: IdentifierTerminal, args: list[str], body: list[IRNode], _end: Token, _macro_end: Token):
        return MacroDefinitionNode(line(name), self.filename, name.value, args, body)

    def macro_definition_args(self, *args: MacroArgumentOperand):
        return [arg.placeholder for arg in args]

    def macro_body(self, *body: IRNode):
        return [node for node in body if node is not None]

    def macro_call(self, name: IdentifierTerminal, args: list[Operand]):
        return MacroCallNode(line(name), self.filename, name.value, args)

    # labels

    def label(self, name: IdentifierTerminal):
        # IDENTIFIER ":"
        return LabelNode(line(name), self.filename, name.value)

    # terminals

    def constant(self, constant: NumberTerminal | StringTerminal):
        return constant

    def IDENTIFIER(self, identifier: Token):
        return IdentifierTerminal(line(identifier), self.filename, identifier.value)

    def STRING(self, string: Token):
        return StringTerminal(line(string), self.filename, string.value)

    def NUMBER(self, number: Token):
        return NumberTerminal(line(number), self.filename, number.value)

    def REGISTER(self, register: Token):
        return RegisterTerminal(line(register), self.filename, register.value)

    def MNEMONIC(self, mnemonic: Token):
        return MnemonicTerminal(line(mnemonic), self.filename, mnemonic.value)
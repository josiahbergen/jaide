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

    
    def start(self, *statements):
        # base level node, return the entire transformed tree.
        # we return a list because generate_ir_nodes() must return a list[IRNode].
        return [s for s in statements if s is not None]

    # instructions

    def instruction(self, mnemonic: MnemonicTerminal, operands: list[Operand] = []):
        return InstructionNode(line(mnemonic), mnemonic.value, operands)

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
        return operand_map[type(terminal)](line(terminal), terminal)

    def pointer_operand(self, register: RegisterTerminal):
        # "[" REGISTER "]"
        return PointerOperand(line(register), register)

    def offset_pointer_operand(self, identifier: IdentifierTerminal, register: RegisterTerminal):
        # "[" IDENTIFIER "+" REGISTER "]"
        return OffsetPointerOperand(line(identifier), identifier, register)

    def relative_pointer_operand(self, identifier: IdentifierTerminal):
        # "[" IDENTIFIER "]"
        return RelativePointerOperand(line(identifier), identifier)

    def macro_arg(self, identifier: IdentifierTerminal):
        # "%" IDENTIFIER
        return MacroArgumentOperand(line(identifier), identifier)

    def expression(self, *operands):
        logger.fatal("transformer: expressions are not yet implemented.", "transformer.py:expression()")

    # directives

    def directive(self, directive: DataDirectiveNode | ImportDirectiveNode):
        # receives an already parsed DataDirectiveNode or ImportDirectiveNode,
        # so just return it.
        return directive

    def import_directive(self, _import: Token, string: StringTerminal):
        # "IMPORT" STRING
        return ImportDirectiveNode(line(string), string.value)

    def org_directive(self, _org: Token, address: NumberTerminal):
        # "ORG" NUMBER
        return OrgDirectiveNode(line(address), address.value)

    def define_directive(self, _define: Token, name: IdentifierTerminal, value: NumberTerminal):
        # "DEFINE" IDENTIFIER NUMBER
        return DefineDirectiveNode(line(name), name.value, value.value)

    def times_directive(self, _times: Token, count: NumberTerminal, value: NumberTerminal):
        # "TIMES" NUMBER NUMBER
        return TimesDirectiveNode(line(count), count.value, value.value)

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
        return DataDirectiveNode(line(_data), items)

    # macros

    def macro_definition(self, _macro: Token, name: IdentifierTerminal, args: list[str], body: list[IRNode], _end: Token, _macro_end: Token):
        return MacroDefinitionNode(line(name), name.value, args, body)

    def macro_definition_args(self, *args: MacroArgumentOperand):
        return [arg.placeholder for arg in args]

    def macro_body(self, *body: IRNode):
        return [node for node in body if node is not None]

    def macro_call(self, name: IdentifierTerminal, args: list[Operand]):
        return MacroCallNode(line(name), name.value, args)

    # labels

    def label(self, name: IdentifierTerminal):
        # IDENTIFIER ":"
        return LabelNode(line(name), name.value)

    # terminals

    def constant(self, constant: NumberTerminal | StringTerminal):
        return constant

    def IDENTIFIER(self, identifier: Token):
        return IdentifierTerminal(line(identifier), identifier.value)

    def STRING(self, string: Token):
        return StringTerminal(line(string), string.value)

    def NUMBER(self, number: Token):
        return NumberTerminal(line(number), number.value)

    def REGISTER(self, register: Token):
        return RegisterTerminal(line(register), register.value)

    # def MACRO(self, keyword: Token):
    #     return KeywordTerminal(line(keyword), keyword.value)

    # def END(self, keyword: Token):
    #     return KeywordTerminal(line(keyword), keyword.value)

    # def DATA(self, keyword: Token):
    #     return DirectiveTerminal(line(keyword), keyword.value)

    # def IMPORT(self, keyword: Token):
    #     return DirectiveTerminal(line(keyword), keyword.value)

    def MNEMONIC(self, mnemonic: Token):
        return MnemonicTerminal(line(mnemonic), mnemonic.value)
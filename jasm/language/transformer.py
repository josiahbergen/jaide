# transformer.py
# jasm transformer
# josiah bergen, march 2026

from jasm.language.ir import Operand


from .ir import (
    IRNode,
    InstructionNode, 
    Operand, 
    Constant,
    RegisterOperand, 
    ImmediateOperand, 
    LabelOperand, 
    PointerOperand,
    OffsetAddressOperand,
    MacroArgumentOperand,
    LabelNode,
    DataDirectiveNode,
    ImportDirectiveNode,
    MacroDefinitionNode,
    MacroCallNode,
)
from ..util.logger import logger
from lark import Transformer, v_args, Token, Tree


def line(token: Token) -> int:
    return token.line or 0

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

    def instruction(self, mnemonic: Token, *operand_list):
        operands = operand_list[0] if operand_list else []
        return InstructionNode(line(mnemonic), mnemonic.value, operands)


    # instructions: operands

    def REGISTER(self, register: Token):
        return RegisterOperand(line(register), register.value)

    def NUMBER(self, number: Token):
        return ImmediateOperand(line(number), number.value)

    def LABELNAME(self, label: Token):
        return LabelOperand(line(label), label.value)

    def pointer_operand(self, reg: RegisterOperand):
        # this function is strange as it essentially mutates the naively parsed RegisterOperand
        # into a PointerOperand, because we now have the knowledge that this is supposed to be one.
        return PointerOperand(reg.line, reg.register)

    def offset_operand(self, label: LabelOperand, register: RegisterOperand):
        line = label.line or register.line # get the line number from wherever
        return OffsetAddressOperand(register.line, label.label, register.register)

    def macro_arg(self, label: LabelOperand):
        # macro arguments contain labels, as this is easier to parse.
        # so, we simply need to convert the LabelOperand back to a MacroArgumentOperand.
        return MacroArgumentOperand(label.line, label.label)

    def expression(self, *operands):
        logger.fatal("transformer: expressions are not yet implemented.", "transformer.py:expression()")

    # directives

    def directive(self, directive: IRNode):
        return directive

    def data_directive(self, *constants: Constant):
        items: list[tuple[DataDirectiveNode.Type, str]] = []

        for constant in constants:
            if isinstance(constant, ImmediateOperand):
                # numbers get converted to ImmediateOperands
                items.append((DataDirectiveNode.Type.NUMBER, constant.value))
            elif isinstance(constant, Constant):
                # not a number? it's a string.
                items.append((DataDirectiveNode.Type.STRING, constant.value))

        return DataDirectiveNode(constants[0].line, items)

    def import_directive(self, string: Constant):
        return ImportDirectiveNode(string.line, string.value)

    def STRING(self, string: Token):
        return Constant(line(string), string.value[1:-1]) # remove quotes, and return a simple string

    # labels

    def label(self, *operands: LabelOperand):
        assert_operand_count(operands, 1, "transformer.py:label()")

        # raw labelnames are initially turned into LabelOperand nodes,
        # so we need to convert them back to a LabelNode.
        label: LabelOperand = operands[0]
        return LabelNode(label.line, label.label)

    # macros

    def macro_definition(self, _keyword: Token, name: LabelOperand, args: list[MacroArgumentOperand], body: list[IRNode], *_end_keywords: Token):
        return MacroDefinitionNode(name.line, name.label, [arg.name for arg in args], body)
 
    def macro_definition_args(self, *args: MacroArgumentOperand):
        return list[MacroArgumentOperand](args)

    def macro_body(self, *body: IRNode):
        return list[IRNode](body)

    def macro_call(self, name: LabelOperand, operands: list[Operand]):
        return MacroCallNode(name.line, name.label, operands)
    
    def operand_list(self, *operands: Operand):
        return list[Operand](operands)
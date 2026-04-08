# labels.py
# label resolution functions.
# josiah bergen, december 2025

from .language.context import AssemblyContext
from .language.ir.base import AlignDirectiveNode, DataDirectiveNode, InstructionNode, LabelNode
from .language.ir.operands import ImmediateOperand, LabelOperand
from .language.ir.terminals import NumberTerminal
from .language.isa import MODES, OPCODE_MAP
from .util.logger import logger


def prepare_instructions(context: AssemblyContext) -> None:
    scope = "labels.py:prepare_instructions()"
    pc = context.origin or 0

    logger.debug("labels: pass 1 (PCs and label definitions)...")

    # pass 1
    # we need to know the size of everything before we can encode it.
    #
    # walk the ir and assign pcs to labels and instructions
    # substitute constants with immediate operands
    # parse and fill alignment directives
    # calculate the size of instructions and data directives
    for node in context.ir:
        node.pc = pc

        if isinstance(node, LabelNode):
            if node.name in context.labels:
                logger.fatal(f'label "{node.name.lower()}" defined multiple times (line {node.line})', scope)
            if node.name in context.constants:
                logger.fatal(f'label "{node.name.lower()}" already defined as a constant (line {node.line})', scope)

            # add the label to the context's labels dictionary.
            logger.debug(f'labels: "{node.name}" defined at PC {pc}')
            context.labels[node.name] = pc
            continue

        if isinstance(node, InstructionNode):
            for i, operand in enumerate(node.operands):
                # search for constants (initially parsed as labels),
                # and replace them with immediate operands.
                if isinstance(operand, LabelOperand) and operand.short_name in context.constants:
                    logger.debug(f"labels: constant operand {operand} -> {context.constants[operand.short_name]} (line {node.line})")
                    num = NumberTerminal(operand.line, operand.filename, str(context.constants[operand.short_name]))
                    node.operands[i] = ImmediateOperand(operand.line, operand.filename, num)

        if isinstance(node, AlignDirectiveNode):
            # calculate the size of the alignment directive.
            node.size = (node.alignment - (pc % node.alignment)) % node.alignment

        # get the size of the node
        size = node.get_size()

        if isinstance(node, InstructionNode):
            # saves a call to get_size() if we do it here.
            node.size = size

        logger.verbose(f"labels: pc {pc} -> {pc + size}")
        pc += size

    logger.debug(f"labels: pass 1 done ({len(context.labels)} labels).")
    logger.debug("labels: pass 2 (label refs, data words, opcodes)...")

    # pass 2
    # every symbol now has an address from pass 1. finish anything that needed that.
    #
    # operands that are still a label are references to code/data labels.
    # if the instruction has an immediate form, swap in the absolute 16-bit address. 
    # branches have no absolute form, leave the operand as label and binary.py will encode it as a pc-relative offset from the next word.
    # identifiers in data directives become 16-bit words.

    # NOTE: this is where PIC would diverge.
    # PIC would need to resolve the labels to their absolute addresses,
    # and then encode the instructions as pc-relative offsets.
    # we don't support PIC yet, so we leave the labels as is.

    for node in context.ir:
        if isinstance(node, InstructionNode):
            for i, operand in enumerate(node.operands):

                # search entire ir for label operands in instructions.
                if not isinstance(operand, LabelOperand):
                    continue

                if operand.name not in context.labels:
                    logger.fatal(f'undefined label "{operand.name.lower()}" on line {node.line}', scope)

                # try IMM encoding: same mnemonic but with immediate operand instead of label operand
                # there's probably a better way to do this.
                candidate_modes = tuple(MODES.IMM if j == i else op.mode for j, op in enumerate(node.operands))
                if (node.mnemonic, candidate_modes) not in OPCODE_MAP:
                    logger.verbose(f"labels: no IMM variant for {node.mnemonic.name} (line {node.line}), keeping RELATIVE")
                    continue

                abs_addr = context.labels[operand.name]
                logger.debug(f"labels: '{operand.name}' -> absolute {abs_addr:#06x} (line {node.line})")

                # swap in the immediate operand
                node.operands[i] = ImmediateOperand(
                    operand.line,
                    operand.filename,
                    NumberTerminal(operand.line, operand.filename, str(abs_addr)),
                )

            # assign addressing mode (encoded via opcode map)
            node.opcode = node.get_opcode()

        elif isinstance(node, DataDirectiveNode):
            # resolve the words in the data directive, 
            # now that we have data for all labels.
            node.data = node.resolve_words(context.labels, context.constants)

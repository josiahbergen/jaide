# labels.py
# label resolution functions.
# josiah bergen, december 2025

from .language.context import AssemblyContext
from .language.ir.base import AlignDirectiveNode, LabelNode, InstructionNode
from .language.ir.operands import ImmediateOperand, LabelOperand
from .language.ir.terminals import NumberTerminal
from .language.isa import OPCODE_MAP, MODES
from .util.logger import logger


def prepare_instructions(context: AssemblyContext) -> None:

    # pass 1: compute the pc positions of all labels and constants.
    # at this point, the only nodes that are left are instructions, data/times/align directives, and labels.
    # macros are now expanded, so the exact order and amount of nodes is known.
    # we actually set the pc for all nodes, not just labels.
    _compute_labels_and_constants(context)

    # pass 2: convert label operands to absolute immediates and compute opcodes.
    # all label positions are now known, so we can resolve references and finalize
    # instruction encoding in a single walk.
    #
    # NOTE: PIC (position-independent code) is not yet implemented.
    # when PIC is added, this pass should be conditional on linkable mode, and
    # label operands in linkable mode should remain as RELATIVE so binary.py
    # emits a pc-relative offset instead of an absolute address.
    _resolve_label_references(context)


def _compute_labels_and_constants(context: AssemblyContext) -> None:
    scope = "labels.py:_compute_labels_and_constants()"

    logger.debug("labels: resolving labels and constants...")
    pc = context.origin or 0  # defaults to 0 if not set

    for node in context.ir:
        node.pc = pc # set the pc for the node

        if isinstance(node, LabelNode):

            if node.name in context.labels.keys():
                logger.fatal(f"label \"{node.name.lower()}\" defined multiple times (line {node.line})", scope)

            if node.name in context.constants.keys():
                logger.fatal(f"label \"{node.name.lower()}\" already defined as a constant (line {node.line})", scope)

            logger.debug(f"labels: \"{node.name}\" defined at PC {pc}")
            context.labels[node.name] = pc  # mangle with filename
            continue

        # resolve constants, parser emits them as labels
        if isinstance(node, InstructionNode):
            for i, operand in enumerate(node.operands):

                # resolve constants
                if isinstance(operand, LabelOperand) and operand.short_name in context.constants:
                    logger.debug(f"labels: populating constant operand {operand} -> {context.constants[operand.short_name]} on line {node.line}")
                    number = NumberTerminal(operand.line, operand.filename, str(context.constants[operand.short_name]))
                    node.operands[i] = ImmediateOperand(operand.line, operand.filename, number)

                # resolve expressions
                # if isinstance(operand, ExpressionOperand):
                #     logger.debug(f"labels: evaluating expression {operand} on line {node.line}")
                #     number = NumberTerminal(operand.line, str(operand.compute()))
                #     node.operands[i] = ImmediateOperand(operand.line, number)

        # we have all the information to calculate the size now!
        if isinstance(node, AlignDirectiveNode):
            node.size = (node.alignment - (pc % node.alignment)) % node.alignment

        size = node.get_size()  # size in words

        if isinstance(node, InstructionNode):
            node.size = size
            # opcode computation is deferred to after pass 2.

        # increment pc!
        logger.verbose(f"labels: pc {pc} -> {pc + size}")
        pc += size

    logger.debug(f"labels: resolved {len(context.labels)} labels.")


def _resolve_label_references(context: AssemblyContext) -> None:
    scope = "labels.py:_resolve_label_references()"

    logger.debug("labels: resolving label references...")

    for node in context.ir:
        if not isinstance(node, InstructionNode):
            continue

        for i, operand in enumerate(node.operands):
            if not isinstance(operand, LabelOperand):
                continue

            if operand.name not in context.labels:
                logger.fatal(f"undefined label \"{operand.name.lower()}\" on line {node.line}", scope)

            # check if swapping this operand to IMM gives a valid opcode
            candidate_modes = tuple(
                MODES.IMM if j == i else op.mode
                for j, op in enumerate(node.operands)
            )
            if (node.mnemonic, candidate_modes) not in OPCODE_MAP:
                # no IMM variant — leave as RELATIVE (e.g. conditional branches)
                logger.verbose(f"labels: no IMM variant for {node.mnemonic.name} on line {node.line}, keeping RELATIVE")
                continue

            abs_addr = context.labels[operand.name]
            logger.debug(f"labels: '{operand.name}' -> absolute {abs_addr:#06x} on line {node.line}")
            node.operands[i] = ImmediateOperand(operand.line, operand.filename, NumberTerminal(operand.line, operand.filename, str(abs_addr)))

        node.opcode = node.get_opcode()

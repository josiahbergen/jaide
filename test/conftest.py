import pytest

from emulator.emulator import Emulator
from jasm.binary import generate_binary
from jasm.labels import prepare_instructions
from jasm.language.context import AssemblyContext
from jasm.parse import parse_text


@pytest.fixture
def cpu():
    return Emulator(verbosity=0)


@pytest.fixture
def load_program(cpu):
    """Use the real assembler and fetch/decode path, without starting devices."""
    def load(source, address=0x7000):
        context = AssemblyContext("<test>", {"linkable": False})
        context.origin = address
        context.ir = parse_text(source, "<test>")
        prepare_instructions(context)
        cpu.bus.load_bytes(address, generate_binary(context))
        cpu.pc.set(address)
        return context

    return load

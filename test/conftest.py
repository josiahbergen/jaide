import pytest

from jaide.emulator import Emulator
from jasm.jasm import assemble_string


@pytest.fixture
def emu():
    """Fresh Emulator instance, cleaned up after the test."""
    e = Emulator(verbosity=-1)
    yield e


@pytest.fixture
def assemble_and_load(emu):
    """Assemble a JASM source string and load the binary into a fresh emulator.

    Uses the in-memory assembler path (no temp files).

    Usage:
        def test_something(assemble_and_load):
            emu = assemble_and_load("mov A, 0x0042")
            emu.step()
            assert emu.reg["A"].value == 0x42
    """
    def _helper(source: str) -> Emulator:
        binary = assemble_string(source)
        emu.bus.load_bytes(0, binary)
        return emu
    return _helper


@pytest.fixture
def assemble_and_load_ram(emu):
    """Assemble a JASM source string and load it into general-purpose RAM at word 0x4200.

    Use this when the program needs to write to labels that would otherwise land
    in the ROM region (word addresses 0x0000–0x01FF).  PC is set to 0x4200 so
    all PC-relative offsets computed by the assembler remain correct at runtime.
    """
    RAM_WORD = 0x2000

    def _helper(source: str) -> Emulator:
        binary = assemble_string(source)
        emu.bus.load_bytes(RAM_WORD, binary)
        emu.pc.set(RAM_WORD)
        return emu

    return _helper

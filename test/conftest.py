import os
import tempfile

import pytest

from jaide.emulator import Emulator
from jasm.jasm import assemble


@pytest.fixture
def emu():
    """Fresh Emulator instance, cleaned up after the test."""
    e = Emulator(verbosity=-1)
    yield e
    e.__del__()


@pytest.fixture
def assemble_and_load(emu):
    """Assemble a JASM source string, load the binary into an emulator instance.

    Usage:
        def test_something(assemble_and_load):
            emu = assemble_and_load("mov A, 0x0042")
            emu.step()
            assert emu.reg["A"].value == 0x42
    """
    def _helper(source: str) -> Emulator:
        with tempfile.TemporaryDirectory() as tmp:
            src_path = os.path.join(tmp, "test.jasm")
            bin_path = os.path.join(tmp, "test.bin")
            with open(src_path, "w") as f:
                f.write(source)
            assemble(src_path, bin_path)
            emu.load_binary(bin_path)
        return emu
    return _helper


@pytest.fixture
def assemble_and_load_ram(emu):
    """Assemble a JASM source string and load it into general-purpose RAM at word 0x4200.

    Use this when the program needs to write to labels that would otherwise land
    in the ROM region (word addresses 0x0000–0x01FF).  PC is set to 0x4200 so
    all PC-relative offsets computed by the assembler remain correct at runtime.
    """
    RAM_WORD = 0x4200

    def _helper(source: str) -> Emulator:
        with tempfile.TemporaryDirectory() as tmp:
            src_path = os.path.join(tmp, "test.jasm")
            bin_path = os.path.join(tmp, "test.bin")
            with open(src_path, "w") as f:
                f.write(source)
            assemble(src_path, bin_path)
            # load_binary addr is a byte offset; word N lives at byte N*2
            emu.load_binary(bin_path, addr=RAM_WORD * 2)
        emu.pc.set(RAM_WORD)
        return emu

    return _helper

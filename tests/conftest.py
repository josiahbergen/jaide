import os
import tempfile
from collections.abc import Callable

import pytest

from jaide.emulator import Emulator
from jasm.jasm import assemble


@pytest.fixture
def emu():
    """Fresh Emulator instance, cleaned up after the test."""
    e = Emulator()
    yield e
    e.__del__()


@pytest.fixture
def assemble_and_load(emu: Emulator) -> Callable[[str], Emulator]:
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
                _ = f.write(source)
            assemble(src_path, bin_path, {"linkable": True})
            emu.load_binary(bin_path)

        return emu

    return _helper

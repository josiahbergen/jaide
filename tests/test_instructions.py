"""Integration tests: assemble snippets, load into emulator, step through, verify state."""

from collections.abc import Callable

from jaide.constants import FLAG_Z
from jaide.emulator import Emulator


class TestMov:
    def test_mov_immediate(self, assemble_and_load: Callable[[str], Emulator]):
        emu = assemble_and_load("mov A, 0x0042")
        emu.step()
        assert emu.reg["A"].value == 0x0042

    def test_mov_reg_to_reg(self, assemble_and_load: Callable[[str], Emulator]):
        emu = assemble_and_load("mov A, 0x00FF\nmov B, A")
        emu.step()
        emu.step()
        assert emu.reg["B"].value == 0x00FF

    def test_mov_large_immediate(self, assemble_and_load: Callable[[str], Emulator]):
        emu = assemble_and_load("mov A, 0xBEEF")
        emu.step()
        assert emu.reg["A"].value == 0xBEEF


class TestArithmetic:
    def test_add_reg_reg(self, assemble_and_load: Callable[[str], Emulator]):
        emu = assemble_and_load("mov A, 0x000A\nmov B, 0x0014\nadd A, B")
        for _ in range(3):
            emu.step()
        assert emu.reg["A"].value == 30

    def test_add_reg_imm(self, assemble_and_load: Callable[[str], Emulator]):
        emu = assemble_and_load("mov A, 0x0005\nadd A, 0x0003")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 8

    def test_sub_reg_reg(self, assemble_and_load: Callable[[str], Emulator]):
        emu = assemble_and_load("mov A, 0x0064\nmov B, 0x0032\nsub A, B")
        for _ in range(3):
            emu.step()
        assert emu.reg["A"].value == 50

    def test_sub_sets_zero(self, assemble_and_load: Callable[[str], Emulator]):
        emu = assemble_and_load("mov A, 0x0005\nsub A, 0x0005")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0
        assert emu.flag_get(FLAG_Z)

    def test_inc(self, assemble_and_load: Callable[[str], Emulator]):
        emu = assemble_and_load("mov A, 0x0009\ninc A")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 10

    def test_dec(self, assemble_and_load: Callable[[str], Emulator]):
        emu = assemble_and_load("mov A, 0x000A\ndec A")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 9


class TestBitwise:
    def test_and(self, assemble_and_load: Callable[[str], Emulator]):
        emu = assemble_and_load("mov A, 0x00FF\nand A, 0x000F")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0x000F

    def test_or(self, assemble_and_load: Callable[[str], Emulator]):
        emu = assemble_and_load("mov A, 0x00F0\nor A, 0x000F")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0x00FF

    def test_xor(self, assemble_and_load: Callable[[str], Emulator]):
        emu = assemble_and_load("mov A, 0x00FF\nxor A, 0x00FF")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0

    def test_not(self, assemble_and_load: Callable[[str], Emulator]):
        emu = assemble_and_load("mov A, 0x00FF\nnot A")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0xFF00

    def test_lsh(self, assemble_and_load: Callable[[str], Emulator]):
        emu = assemble_and_load("mov A, 0x0001\nlsh A, 0x0004")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0x0010

    def test_rsh(self, assemble_and_load: Callable[[str], Emulator]):
        emu = assemble_and_load("mov A, 0x0100\nrsh A, 0x0004")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0x0010


class TestStack:
    def test_push_pop(self, assemble_and_load: Callable[[str], Emulator]):
        emu = assemble_and_load("mov A, 0x1234\npush A\nmov A, 0x0000\npop B")
        for _ in range(4):
            emu.step()
        assert emu.reg["B"].value == 0x1234
        assert emu.reg["A"].value == 0

    def test_push_immediate(self, assemble_and_load: Callable[[str], Emulator]):
        emu = assemble_and_load("push 0xABCD\npop A")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0xABCD


class TestMemory:
    def test_put_get(self, assemble_and_load: Callable[[str], Emulator]):
        # put value 0xCAFE at address 0x5000, then get it back into C
        emu = assemble_and_load(
            "mov A, 0x5000\n"
            + "mov B, 0xCAFE\n"
            + "put [A], B\n"
            + "mov B, 0x0000\n"
            + "get C, [A]\n"
        )
        for _ in range(5):
            emu.step()
        assert emu.reg["C"].value == 0xCAFE


class TestJump:
    def test_jmp_skips(self, assemble_and_load: Callable[[str], Emulator]):
        # jmp over the first mov to A, so A stays 0 and B gets set
        src = "jmp skip\nmov A, 0x00FF\nskip:\nmov B, 0x0042\n"
        emu = assemble_and_load(src)
        emu.step()  # jmp
        emu.step()  # mov B
        assert emu.reg["A"].value == 0
        assert emu.reg["B"].value == 0x0042

    def test_jz_taken(self, assemble_and_load: Callable[[str], Emulator]):
        src = (
            "mov A, 0x0001\n"
            "sub A, 0x0001\n"  # A=0, zero flag set
            "jz done\n"
            "mov B, 0x00FF\n"  # should be skipped
            "done:\n"
            "mov C, 0x0042\n"
        )
        emu = assemble_and_load(src)
        for _ in range(4):
            emu.step()
        assert emu.reg["B"].value == 0  # skipped
        assert emu.reg["C"].value == 0x0042

    def test_jnz_not_taken(self, assemble_and_load: Callable[[str], Emulator]):
        src = (
            "mov A, 0x0001\n"
            "sub A, 0x0001\n"  # zero flag set
            "jnz skip\n"
            "mov B, 0x0042\n"  # should execute
            "skip:\n"
            "nop\n"
        )
        emu = assemble_and_load(src)
        for _ in range(4):
            emu.step()
        assert emu.reg["B"].value == 0x0042


class TestCallRet:
    def test_call_and_ret(self, assemble_and_load: Callable[[str], Emulator]):
        src = (
            "call myfunc\n"
            "mov B, 0x0042\n"  # return here
            "jmp done\n"
            "myfunc:\n"
            "mov A, 0x00FF\n"
            "ret\n"
            "done:\n"
            "nop\n"
        )
        emu = assemble_and_load(src)
        emu.step()  # call myfunc
        emu.step()  # mov A, 0xFF
        emu.step()  # ret
        emu.step()  # mov B, 0x42
        assert emu.reg["A"].value == 0x00FF
        assert emu.reg["B"].value == 0x0042

"""Unit tests for the ALU core operations: _add_core, _sub_core, _lsh_core, _rsh_core."""

from jaide.constants import FLAG_C, FLAG_N, FLAG_O, FLAG_Z
from jaide.emulator import Emulator


class TestAddCore:
    def test_simple_addition(self, emu: Emulator):
        result = emu._add_core(10, 20)  # pyright: ignore[reportPrivateUsage]
        assert result == 30
        assert not emu.flag_get(FLAG_Z)
        assert not emu.flag_get(FLAG_C)
        assert not emu.flag_get(FLAG_N)

    def test_zero_result(self, emu: Emulator):
        result = emu._add_core(0, 0)  # pyright: ignore[reportPrivateUsage]
        assert result == 0
        assert emu.flag_get(FLAG_Z)
        assert not emu.flag_get(FLAG_C)

    def test_carry_out(self, emu: Emulator):
        result = emu._add_core(0xFFFF, 1)  # pyright: ignore[reportPrivateUsage]
        assert result == 0
        assert emu.flag_get(FLAG_Z)
        assert emu.flag_get(FLAG_C)

    def test_carry_no_zero(self, emu: Emulator):
        result = emu._add_core(0xFFFF, 2)  # pyright: ignore[reportPrivateUsage]
        assert result == 1
        assert not emu.flag_get(FLAG_Z)
        assert emu.flag_get(FLAG_C)

    def test_carry_in(self, emu: Emulator):
        result = emu._add_core(10, 20, carry_in=1)  # pyright: ignore[reportPrivateUsage]
        assert result == 31

    def test_carry_in_causes_overflow(self, emu: Emulator):
        result = emu._add_core(0xFFFF, 0, carry_in=1)  # pyright: ignore[reportPrivateUsage]
        assert result == 0
        assert emu.flag_get(FLAG_Z)
        assert emu.flag_get(FLAG_C)

    def test_overflow_positive(self, emu: Emulator):
        # 0x0040 + 0x0060 = 0x00A0 — both operands have bit 7 clear,
        # result has bit 7 set → overflow
        result = emu._add_core(0x0040, 0x0060)  # pyright: ignore[reportPrivateUsage]
        assert result == 0x00A0
        assert emu.flag_get(FLAG_O)

    def test_no_overflow_different_signs(self, emu: Emulator):
        # operands differ in bit 7 → overflow cannot occur
        result = emu._add_core(0x0080, 0x0001)  # pyright: ignore[reportPrivateUsage]
        assert result == 0x0081
        assert not emu.flag_get(FLAG_O)

    def test_large_values_no_carry(self, emu: Emulator):
        result = emu._add_core(0x7FFF, 0)  # pyright: ignore[reportPrivateUsage]
        assert result == 0x7FFF
        assert not emu.flag_get(FLAG_C)
        assert not emu.flag_get(FLAG_Z)


class TestSubCore:
    def test_simple_subtraction(self, emu: Emulator):
        result = emu._sub_core(30, 10)  # pyright: ignore[reportPrivateUsage]
        assert result == 20
        assert not emu.flag_get(FLAG_Z)
        assert emu.flag_get(FLAG_C)  # no borrow → carry set

    def test_zero_result(self, emu: Emulator):
        result = emu._sub_core(42, 42)  # pyright: ignore[reportPrivateUsage]
        assert result == 0
        assert emu.flag_get(FLAG_Z)
        assert emu.flag_get(FLAG_C)

    def test_borrow(self, emu: Emulator):
        result = emu._sub_core(0, 1)  # pyright: ignore[reportPrivateUsage]
        assert result == 0xFFFF
        assert not emu.flag_get(FLAG_C)  # borrow → carry clear

    def test_borrow_in(self, emu: Emulator):
        result = emu._sub_core(10, 5, borrow_in=1)  # pyright: ignore[reportPrivateUsage]
        assert result == 4

    def test_borrow_in_causes_borrow(self, emu: Emulator):
        result = emu._sub_core(5, 5, borrow_in=1)  # pyright: ignore[reportPrivateUsage]
        assert result == 0xFFFF
        assert not emu.flag_get(FLAG_C)

    def test_overflow(self, emu: Emulator):
        # 0x0080 - 0x0001: operands differ in bit 7, result bit 7 differs from a
        # a=0x0080 (bit7=1), b=0x0001 (bit7=0) → (a^b)&0x80 != 0
        # result=0x007F (bit7=0), (a^result)&0x80 != 0 → overflow
        result = emu._sub_core(0x0080, 0x0001)  # pyright: ignore[reportPrivateUsage]
        assert result == 0x007F
        assert emu.flag_get(FLAG_O)

    def test_no_overflow(self, emu: Emulator):
        result = emu._sub_core(100, 50)  # pyright: ignore[reportPrivateUsage]
        assert result == 50
        assert not emu.flag_get(FLAG_O)


class TestLshCore:
    def test_shift_left_by_1(self, emu: Emulator):
        result = emu._lsh_core(0x0001, 1)  # pyright: ignore[reportPrivateUsage]
        assert result == 0x0002
        assert not emu.flag_get(FLAG_C)
        assert not emu.flag_get(FLAG_Z)

    def test_shift_left_carry(self, emu: Emulator):
        # bit 15 set → shifting left by 1 pushes it out → carry
        result = emu._lsh_core(0x8000, 1)  # pyright: ignore[reportPrivateUsage]
        assert result == 0
        assert emu.flag_get(FLAG_C)
        assert emu.flag_get(FLAG_Z)

    def test_shift_left_by_4(self, emu: Emulator):
        result = emu._lsh_core(0x00FF, 4)  # pyright: ignore[reportPrivateUsage]
        assert result == 0x0FF0
        assert not emu.flag_get(FLAG_C)

    def test_shift_left_full(self, emu: Emulator):
        result = emu._lsh_core(0x0001, 16)  # pyright: ignore[reportPrivateUsage]
        assert result == 0  # shifted entirely out
        assert emu.flag_get(FLAG_Z)

    def test_shift_zero(self, emu: Emulator):
        result = emu._lsh_core(0, 5)  # pyright: ignore[reportPrivateUsage]
        assert result == 0
        assert emu.flag_get(FLAG_Z)


class TestRshCore:
    def test_shift_right_by_1(self, emu: Emulator):
        result = emu._rsh_core(0x0002, 1)  # pyright: ignore[reportPrivateUsage]
        assert result == 0x0001
        assert not emu.flag_get(FLAG_C)

    def test_shift_right_carry(self, emu: Emulator):
        # bit 0 set, shifting right by 1 → carry
        result = emu._rsh_core(0x0001, 1)  # pyright: ignore[reportPrivateUsage]
        assert result == 0
        assert emu.flag_get(FLAG_C)
        assert emu.flag_get(FLAG_Z)

    def test_shift_right_by_4(self, emu: Emulator):
        result = emu._rsh_core(0xFF00, 4)  # pyright: ignore[reportPrivateUsage]
        assert result == 0x0FF0
        assert not emu.flag_get(FLAG_C)

    def test_shift_right_high_bit(self, emu: Emulator):
        result = emu._rsh_core(0x8000, 1)  # pyright: ignore[reportPrivateUsage]
        assert result == 0x4000
        assert not emu.flag_get(FLAG_C)

    def test_shift_zero(self, emu: Emulator):
        result = emu._rsh_core(0, 3)  # pyright: ignore[reportPrivateUsage]
        assert result == 0
        assert emu.flag_get(FLAG_Z)

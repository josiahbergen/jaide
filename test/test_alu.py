"""Unit tests for the ALU core operations: _add_core, _sub_core, _lsh_core, _rsh_core."""

from jaide.constants import FLAG_C, FLAG_Z, FLAG_N, FLAG_O


class TestAddCore:

    def test_simple_addition(self, emu):
        result = emu._add_core(10, 20)
        assert result == 30
        assert not emu.flag_get(FLAG_Z)
        assert not emu.flag_get(FLAG_C)
        assert not emu.flag_get(FLAG_N)

    def test_zero_result(self, emu):
        result = emu._add_core(0, 0)
        assert result == 0
        assert emu.flag_get(FLAG_Z)
        assert not emu.flag_get(FLAG_C)

    def test_carry_out(self, emu):
        result = emu._add_core(0xFFFF, 1)
        assert result == 0
        assert emu.flag_get(FLAG_Z)
        assert emu.flag_get(FLAG_C)

    def test_carry_no_zero(self, emu):
        result = emu._add_core(0xFFFF, 2)
        assert result == 1
        assert not emu.flag_get(FLAG_Z)
        assert emu.flag_get(FLAG_C)

    def test_carry_in(self, emu):
        result = emu._add_core(10, 20, carry_in=1)
        assert result == 31

    def test_carry_in_causes_overflow(self, emu):
        result = emu._add_core(0xFFFF, 0, carry_in=1)
        assert result == 0
        assert emu.flag_get(FLAG_Z)
        assert emu.flag_get(FLAG_C)

    def test_overflow_positive(self, emu):
        # 0x0040 + 0x0060 = 0x00A0 — both operands have bit 7 clear,
        # result has bit 7 set → overflow
        result = emu._add_core(0x0040, 0x0060)
        assert result == 0x00A0
        assert emu.flag_get(FLAG_O)

    def test_no_overflow_different_signs(self, emu):
        # operands differ in bit 7 → overflow cannot occur
        result = emu._add_core(0x0080, 0x0001)
        assert result == 0x0081
        assert not emu.flag_get(FLAG_O)

    def test_large_values_no_carry(self, emu):
        result = emu._add_core(0x7FFF, 0)
        assert result == 0x7FFF
        assert not emu.flag_get(FLAG_C)
        assert not emu.flag_get(FLAG_Z)


class TestSubCore:

    def test_simple_subtraction(self, emu):
        result = emu._sub_core(30, 10)
        assert result == 20
        assert not emu.flag_get(FLAG_Z)
        assert emu.flag_get(FLAG_C)  # no borrow → carry set

    def test_zero_result(self, emu):
        result = emu._sub_core(42, 42)
        assert result == 0
        assert emu.flag_get(FLAG_Z)
        assert emu.flag_get(FLAG_C)

    def test_borrow(self, emu):
        result = emu._sub_core(0, 1)
        assert result == 0xFFFF
        assert not emu.flag_get(FLAG_C)  # borrow → carry clear

    def test_borrow_in(self, emu):
        result = emu._sub_core(10, 5, borrow_in=1)
        assert result == 4

    def test_borrow_in_causes_borrow(self, emu):
        result = emu._sub_core(5, 5, borrow_in=1)
        assert result == 0xFFFF
        assert not emu.flag_get(FLAG_C)

    def test_overflow(self, emu):
        # 0x0080 - 0x0001: operands differ in bit 7, result bit 7 differs from a
        # a=0x0080 (bit7=1), b=0x0001 (bit7=0) → (a^b)&0x80 != 0
        # result=0x007F (bit7=0), (a^result)&0x80 != 0 → overflow
        result = emu._sub_core(0x0080, 0x0001)
        assert result == 0x007F
        assert emu.flag_get(FLAG_O)

    def test_no_overflow(self, emu):
        result = emu._sub_core(100, 50)
        assert result == 50
        assert not emu.flag_get(FLAG_O)


class TestLshCore:

    def test_shift_left_by_1(self, emu):
        result = emu._lsh_core(0x0001, 1)
        assert result == 0x0002
        assert not emu.flag_get(FLAG_C)
        assert not emu.flag_get(FLAG_Z)

    def test_shift_left_carry(self, emu):
        # bit 15 set → shifting left by 1 pushes it out → carry
        result = emu._lsh_core(0x8000, 1)
        assert result == 0
        assert emu.flag_get(FLAG_C)
        assert emu.flag_get(FLAG_Z)

    def test_shift_left_by_4(self, emu):
        result = emu._lsh_core(0x00FF, 4)
        assert result == 0x0FF0
        assert not emu.flag_get(FLAG_C)

    def test_shift_left_full(self, emu):
        result = emu._lsh_core(0x0001, 16)
        assert result == 0  # shifted entirely out
        assert emu.flag_get(FLAG_Z)

    def test_shift_zero(self, emu):
        result = emu._lsh_core(0, 5)
        assert result == 0
        assert emu.flag_get(FLAG_Z)


class TestRshCore:

    def test_shift_right_by_1(self, emu):
        result = emu._rsh_core(0x0002, 1)
        assert result == 0x0001
        assert not emu.flag_get(FLAG_C)

    def test_shift_right_carry(self, emu):
        # bit 0 set, shifting right by 1 → carry
        result = emu._rsh_core(0x0001, 1)
        assert result == 0
        assert emu.flag_get(FLAG_C)
        assert emu.flag_get(FLAG_Z)

    def test_shift_right_by_4(self, emu):
        result = emu._rsh_core(0xFF00, 4)
        assert result == 0x0FF0
        assert not emu.flag_get(FLAG_C)

    def test_shift_right_high_bit(self, emu):
        result = emu._rsh_core(0x8000, 1)
        assert result == 0x4000
        assert not emu.flag_get(FLAG_C)

    def test_shift_zero(self, emu):
        result = emu._rsh_core(0, 3)
        assert result == 0
        assert emu.flag_get(FLAG_Z)


class TestAsrCore:

    def test_shift_positive(self, emu):
        # 0x0010 >> 2 == 0x0004, sign bit clear → stays positive
        result = emu._asr_core(0x0010, 2)
        assert result == 0x0004
        assert not emu.flag_get(FLAG_Z)
        assert not emu.flag_get(FLAG_C)

    def test_preserves_sign_bit(self, emu):
        # 0x8000 (most-negative) >> 1 == 0xC000 (sign extended)
        result = emu._asr_core(0x8000, 1)
        assert result == 0xC000
        assert not emu.flag_get(FLAG_Z)

    def test_carry_last_bit_shifted_out(self, emu):
        # 0x0003 >> 1: last bit shifted out is bit 0 = 1 → carry
        result = emu._asr_core(0x0003, 1)
        assert result == 0x0001
        assert emu.flag_get(FLAG_C)

    def test_no_carry_when_last_bit_zero(self, emu):
        # 0x0004 >> 1: last bit shifted out is bit 0 = 0 → no carry
        result = emu._asr_core(0x0004, 1)
        assert result == 0x0002
        assert not emu.flag_get(FLAG_C)

    def test_zero_result(self, emu):
        result = emu._asr_core(0x0001, 1)
        assert result == 0
        assert emu.flag_get(FLAG_Z)
        assert emu.flag_get(FLAG_C)

    def test_negative_fills_with_ones(self, emu):
        # 0xFFFF (-1 signed) >> 4 should remain 0xFFFF
        result = emu._asr_core(0xFFFF, 4)
        assert result == 0xFFFF
        assert not emu.flag_get(FLAG_Z)

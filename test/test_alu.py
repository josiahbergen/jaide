import pytest

from emulator.constants import USER_MODE


@pytest.mark.parametrize("operand", ["b", "immediate"])
@pytest.mark.parametrize("operation,left,right,carry,result,flags", [
    ("add", 0xFFFF, 1, 0, 0, 0b0011),
    ("add", 0x7FFF, 1, 0, 0x8000, 0b1100),
    ("add", 0x8000, 0x8000, 0, 0, 0b1011),
    ("adc", 0xFFFF, 0, 1, 0, 0b0011),
    ("adc", 0x7FFF, 0, 1, 0x8000, 0b1100),
    ("adc", 1, 2, 0, 3, 0),
    ("sub", 0, 1, 0, 0xFFFF, 0b0100),
    ("sub", 5, 5, 0, 0, 0b0011),
    ("sub", 0x8000, 1, 0, 0x7FFF, 0b1001),
    ("sub", 0x7FFF, 0xFFFF, 0, 0x8000, 0b1100),
    # SBC consumes C as a borrow, as specified in inst.txt.
    ("sbc", 0, 0, 1, 0xFFFF, 0b0100),
    ("sbc", 5, 3, 1, 1, 0b0001),
    ("sbc", 5, 3, 0, 2, 0b0001),
    ("mul", 0x8000, 2, 0, 0, 0b0011),
    ("mul", 0x4000, 2, 0, 0x8000, 0b0100),
    ("div", 7, 2, 0, 3, 0b0001),
    ("div", 6, 2, 0, 3, 0),
    ("div", 1, 2, 0, 0, 0b0011),
    ("div", 0xFFFF, 1, 0, 0xFFFF, 0b0100),
    ("mod", 7, 2, 0, 1, 0),
    ("mod", 6, 2, 0, 0, 0b0010),
    ("mod", 0x8000, 0xFFFF, 0, 0x8000, 0b0100),
    ("asr", 0x8001, 1, 0, 0xC000, 0b0101),
    ("asr", 0x8000, 16, 0, 0xFFFF, 0b0101),
    ("asr", 0x8000, 0, 0, 0x8000, 0b0100),
])
def test_math_result_and_all_flags(cpu, load_program, operand, operation, left, right, carry, result, flags):
    source = "b" if operand == "b" else hex(right)
    load_program(f"{operation} a, {source}\n")
    cpu.reg["A"].set(left)
    cpu.reg["B"].set(right)
    cpu.f.set(0xE | carry)  # stale flags must be cleared as well as set

    cpu.step()

    assert cpu.reg["A"].value == result
    assert cpu.reg["B"].value == right
    assert cpu.f.value == flags


@pytest.mark.parametrize("instruction,start,result,flags", [
    ("inc", 0xFFFF, 0, 3), ("inc", 0x7FFF, 0x8000, 12),
    ("dec", 0, 0xFFFF, 4), ("dec", 0x8000, 0x7FFF, 9),
])
def test_unary_math(cpu, load_program, instruction, start, result, flags):
    load_program(f"{instruction} a\n")
    cpu.reg["A"].set(start)
    cpu.step()
    assert (cpu.reg["A"].value, cpu.f.value) == (result, flags)


@pytest.mark.parametrize("instruction,left,right,result", [
    ("and", 0xAAAA, 0x5555, 0), ("or", 0x8000, 1, 0x8001),
    ("xor", 0xFFFF, 0xFFFF, 0), ("not", 0xFFFF, 0, 0),
    ("not", 0, 0, 0xFFFF),
])
@pytest.mark.parametrize("operand", ["b", "immediate"])
def test_bitwise_operations_only_update_zero_flag(cpu, load_program, instruction, left, right, result, operand):
    source = "b" if operand == "b" else hex(right)
    load_program(f"{instruction} a" + ("\n" if instruction == "not" else f", {source}\n"))
    cpu.reg["A"].set(left)
    cpu.reg["B"].set(right)
    cpu.f.set(0xD | (2 if result else 0))
    cpu.step()
    assert cpu.reg["A"].value == result
    assert cpu.f.value == 0xD | (2 if result == 0 else 0)


@pytest.mark.parametrize("operand", ["b", "5"])
def test_compare_sets_flags_without_changing_operands(cpu, load_program, operand):
    load_program(f"cmp a, {operand}\n")
    cpu.reg["A"].set(5)
    cpu.reg["B"].set(5)
    cpu.f.set(0xF)
    cpu.step()
    assert (cpu.reg["A"].value, cpu.reg["B"].value, cpu.f.value) == (5, 5, 3)


@pytest.mark.parametrize("operation", ["div", "mod"])
@pytest.mark.parametrize("operand", ["b", "0"])
def test_zero_divisor_enters_kernel_with_faulting_pc(cpu, load_program, operation, operand):
    cpu.mb.set(1)
    load_program(f"{operation} a, {operand}\n")
    cpu.reg["A"].set(123)
    cpu.reg["B"].set(0)
    cpu.sp.set(0xAFFF)
    cpu.f.set(9)
    cpu.mode = USER_MODE
    cpu.ie = True
    cpu.step()
    assert cpu.pc.value == 0x0100
    assert cpu.reg["A"].value == 123
    assert not cpu.ie
    assert [cpu.bus.read16(cpu.sp.value + i) for i in range(7)] == [0x7000, 0xAFFF, 9, 1, USER_MODE, 0, 2]


@pytest.mark.parametrize("operand", ["b", "immediate"])
@pytest.mark.parametrize("operation,value,count,result,carry", [
    ("lsh", 1, 0, 1, 0),
    ("rsh", 1, 0, 1, 0),
    ("lsh", 0x8001, 1, 2, 1), ("rsh", 0x8001, 1, 0x4000, 1),
    ("lsh", 0xFFFF, 16, 0, 1), ("rsh", 0xFFFF, 16, 0, 1),
    ("lsh", 1, 17, 0, 0),
    ("rsh", 0xFFFF, 17, 0, 0),
])
def test_logical_shift_result_zero_and_carry(cpu, load_program, operation, value, count, result, carry, operand):
    source = "b" if operand == "b" else str(count)
    load_program(f"{operation} a, {source}\n")
    cpu.reg["A"].set(value)
    cpu.reg["B"].set(count)
    cpu.step()
    assert cpu.reg["A"].value == result
    assert cpu.flag_get(0) == bool(carry)
    assert cpu.flag_get(1) == (result == 0)

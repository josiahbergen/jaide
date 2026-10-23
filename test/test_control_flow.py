import pytest


@pytest.mark.parametrize("branch,flags,taken", [
    ("jz", 2, True), ("jz", 0, False), ("jnz", 0, True), ("jnz", 2, False),
    ("jc", 1, True), ("jc", 0, False), ("jnc", 0, True), ("jnc", 1, False),
    ("ja", 1, True), ("ja", 3, False), ("jae", 1, True), ("jae", 0, False),
    ("jb", 0, True), ("jb", 1, False), ("jbe", 3, True), ("jbe", 1, False),
    ("jg", 12, True), ("jg", 14, False), ("jge", 12, True), ("jge", 4, False),
    ("jl", 8, True), ("jl", 12, False), ("jle", 2, True), ("jle", 12, False),
])
def test_conditional_branches_use_signed_relative_offset_from_next_instruction(cpu, load_program, branch, flags, taken):
    context = load_program(f"{branch} target\nnop\ntarget:\nnop\n")
    cpu.f.set(flags)
    cpu.step()
    assert cpu.pc.value == (context.labels["<TEST>__TARGET"] if taken else 0x7002)
    assert cpu.f.value == flags


def test_backward_branch_loop_and_compare(cpu, load_program):
    context = load_program("mov a, 3\nloop:\ndec a\ncmp a, 0\njnz loop\ndone:\nnop\n")
    for _ in range(10):
        cpu.step()
    assert cpu.reg["A"].value == 0
    assert cpu.pc.value == context.labels["<TEST>__DONE"]
    assert cpu.f.value == 3


@pytest.mark.parametrize("target", ["routine", "b"])
def test_call_and_return_preserve_stack_and_resume_after_full_instruction(cpu, load_program, target):
    context = load_program(f"call {target}\nresume:\nnop\nroutine:\ninc a\nret\n")
    cpu.reg["B"].set(context.labels["<TEST>__ROUTINE"])
    original_sp = cpu.sp.value
    cpu.step()
    assert cpu.pc.value == context.labels["<TEST>__ROUTINE"]
    assert cpu.sp.value == original_sp - 1
    assert cpu.bus.read16(cpu.sp.value) == context.labels["<TEST>__RESUME"]
    cpu.step()
    cpu.step()
    assert (cpu.pc.value, cpu.sp.value, cpu.reg["A"].value) == (context.labels["<TEST>__RESUME"], original_sp, 1)

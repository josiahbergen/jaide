import pytest

from emulator.constants import SUPERVISOR_MODE, USER_MODE
from emulator.exceptions import InvalidInstructionFault, ProtectionFault
from emulator.handlers import handle_syscall, handle_transfer


def context_state(cpu):
    return ([register.value for register in cpu.reg.values()], cpu.ssp.value, cpu.mode, cpu.ie, cpu.waiting)


@pytest.mark.parametrize("bank", [1, 31])
@pytest.mark.parametrize("user_sp", [0x7000, 0xAFFF])
def test_syscall_frame_and_transfer_round_trip(cpu, load_program, bank, user_sp):
    cpu.mb.set(bank)
    load_program("syscall\nnop\n")
    load_program("transfer\n", address=0x0100)
    cpu.pc.set(0x7000)
    cpu.sp.set(user_sp)
    cpu.f.set(0x000F)
    cpu.ssp.set(0xFD80)
    for index, name in enumerate("ABCDEXYZ"):
        cpu.reg[name].set(0x1230 + index)
    general_registers = [cpu.reg[name].value for name in "ABCDEXYZ"]
    cpu.mode = USER_MODE
    cpu.ie = True

    cpu.step()

    assert (cpu.mode, cpu.ie, cpu.pc.value, cpu.sp.value) == (SUPERVISOR_MODE, False, 0x0100, 0xFD79)
    # Wire contract: pc, sp, flags, bank, mode, kind (syscall=2), detail.
    assert [cpu.bus.read16(cpu.sp.value + i) for i in range(7)] == [0x7001, user_sp, 0xF, bank, USER_MODE, 2, 0x1230]
    assert [cpu.reg[name].value for name in "ABCDEXYZ"] == general_registers

    cpu.step()

    assert (cpu.pc.value, cpu.sp.value, cpu.f.value, cpu.mb.value) == (0x7001, user_sp, 0xF, bank)
    assert (cpu.mode, cpu.ie, cpu.waiting, cpu.ssp.value) == (USER_MODE, True, False, 0xFD80)
    assert [cpu.reg[name].value for name in "ABCDEXYZ"] == general_registers
    cpu.step()
    assert cpu.pc.value == 0x7002


@pytest.mark.parametrize("field,value", [
    (0, 0x6FFF), (0, 0xB000), (1, 0x6FFF), (1, 0xB000),
    (2, 0x0010), (2, 0x8000), (3, 0), (3, 32), (4, 2), (4, 0xFFFF),
])
def test_transfer_rejects_invalid_frame_without_changing_state(cpu, field, value):
    cpu.sp.set(0xFD80)
    frame = [0x7000, 0xAFFF, 0xF, 1, USER_MODE, 2, 0x1234]
    frame[field] = value
    for offset, word in enumerate(frame):
        cpu.bus.write16(cpu.sp.value + offset, word)
    cpu.f.set(5)
    cpu.waiting = True
    before = context_state(cpu)

    with pytest.raises(ProtectionFault):
        handle_transfer(cpu, ())

    assert context_state(cpu) == before
    assert [cpu.bus.read16(cpu.sp.value + i) for i in range(7)] == frame


def test_transfer_to_supervisor_restores_context_and_disables_interrupts(cpu):
    cpu.sp.set(0xFD80)
    frame = [0x1234, 0xFD80, 0xA, 0, SUPERVISOR_MODE, 1, 4]
    for offset, word in enumerate(frame):
        cpu.bus.write16(cpu.sp.value + offset, word)
    cpu.ie = True
    cpu.waiting = True
    saved_ssp = cpu.ssp.value

    handle_transfer(cpu, ())

    assert (cpu.pc.value, cpu.sp.value, cpu.f.value, cpu.mb.value) == tuple(frame[:4])
    assert (cpu.mode, cpu.ie, cpu.waiting, cpu.ssp.value) == (SUPERVISOR_MODE, False, False, saved_ssp)


@pytest.mark.parametrize("pc,sp,bank,flags", [
    (0x7000, 0xAFFF, 1, 0), (0xAFFF, 0x7000, 31, 0xF),
])
def test_transfer_accepts_user_context_boundaries(cpu, pc, sp, bank, flags):
    cpu.sp.set(0xFD80)
    frame = [pc, sp, flags, bank, USER_MODE, 0xFFFF, 0xFFFF]
    for offset, word in enumerate(frame):
        cpu.bus.write16(cpu.sp.value + offset, word)
    cpu.waiting = True

    handle_transfer(cpu, ())

    assert (cpu.pc.value, cpu.sp.value, cpu.f.value, cpu.mb.value) == (pc, sp, flags, bank)
    assert (cpu.ssp.value, cpu.mode, cpu.ie, cpu.waiting) == (0xFD87, USER_MODE, True, False)


@pytest.mark.parametrize("handler,mode,error", [
    (handle_syscall, SUPERVISOR_MODE, InvalidInstructionFault),
    (handle_transfer, USER_MODE, ProtectionFault),
])
def test_transition_in_wrong_mode_is_rejected_atomically(cpu, handler, mode, error):
    cpu.mode = mode
    before = context_state(cpu)
    with pytest.raises(error):
        handler(cpu, ())
    assert context_state(cpu) == before

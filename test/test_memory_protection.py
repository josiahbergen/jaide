import pytest

from emulator.constants import USER_MODE
from emulator.exceptions import ProtectionFault


@pytest.mark.parametrize("address", [0x7000, 0xAFFF])
def test_bank_window_boundaries_are_isolated(cpu, address):
    for bank, value in [(0, 0x1234), (1, 0xABCD), (31, 0xFFFF)]:
        cpu.mb.set(bank)
        cpu.bus.write16(address, value)
    for bank, value in [(0, 0x1234), (1, 0xABCD), (31, 0xFFFF)]:
        cpu.mb.set(bank)
        assert cpu.bus.read16(address) == value


@pytest.mark.parametrize("address", [0x6FFF, 0xB000, 0x4000, 0x4FFF, 0x5000, 0xFDFF])
def test_memory_outside_bank_window_is_shared(cpu, address):
    cpu.mb.set(1)
    cpu.bus.write16(address, 0xABCD)
    cpu.mb.set(31)
    assert cpu.bus.read16(address) == 0xABCD


@pytest.mark.parametrize("address", [0, 0xFF, 0x100, 0x4000, 0x6FFF, 0xB000, 0xFDFF, 0xFEFF, 0xFF00, 0xFFFF])
@pytest.mark.parametrize("access", ["read", "write", "fetch"])
def test_user_cannot_access_protected_memory_or_mmio(cpu, monkeypatch, address, access):
    def forbidden_mmio(*args):
        pytest.fail("protection must run before MMIO side effects")

    monkeypatch.setattr(cpu.bus, "mmio_read", forbidden_mmio)
    monkeypatch.setattr(cpu.bus, "mmio_write", forbidden_mmio)
    cpu.mb.set(1)
    cpu.pc.set(address)
    cpu.mode = USER_MODE
    with pytest.raises(ProtectionFault):
        if access == "read":
            cpu.bus.read16(address)
        elif access == "write":
            cpu.bus.write16(address, 0x1234)
        else:
            cpu.fetch()
    assert cpu.pc.value == address


@pytest.mark.parametrize("address", [0x7000, 0xAFFF])
def test_user_can_access_both_ends_of_own_bank(cpu, address):
    cpu.mb.set(31)
    cpu.mode = USER_MODE
    cpu.bus.write16(address, 0x12345)
    assert cpu.bus.read16(address) == 0x2345


def test_user_cannot_switch_banks(cpu, load_program):
    cpu.mb.set(1)
    load_program("mov mb, 31\n")
    cpu.sp.set(0xAFFF)
    cpu.mode = USER_MODE
    cpu.step()
    assert cpu.mb.value == 1
    assert cpu.pc.value == 0x0100
    assert [cpu.bus.read16(cpu.sp.value + i) for i in range(7)][3:] == [1, USER_MODE, 0, 1]

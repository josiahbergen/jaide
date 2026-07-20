import pytest

from jaide.bus import MemoryBus
from jaide.devices.disk import COMMAND_READ, SECTOR_WORDS, Disk


@pytest.fixture
def bus_and_bank():
    selected_bank = [0]
    return MemoryBus(lambda: selected_bank[0]), selected_bank


def test_load_bytes_uses_word_addresses_and_can_initialize_rom(bus_and_bank):
    bus, _ = bus_and_bank

    bus.load_bytes(0x0100, b"\x34\x12")
    bus.load_bytes(0x0000, b"\x78\x56")

    assert bus.read16(0x0100) == 0x1234
    assert bus.read16(0x0000) == 0x5678


def test_peek_does_not_trigger_mmio_read_side_effect():
    reads = 0

    def read(_address: int) -> int:
        nonlocal reads
        reads += 1
        return 0x1234

    bus = MemoryBus(lambda: 0, mmio_read=read)

    assert bus.peek16(0xFE01) == 0
    assert reads == 0
    assert bus.read16(0xFE01) == 0x1234
    assert reads == 1


def test_explicit_bank_access_can_latch_dma_target(bus_and_bank):
    bus, selected_bank = bus_and_bank
    selected_bank[0] = 1
    bus.write16(0x7000, 0x1111)

    selected_bank[0] = 2
    bus.write16(0x7000, 0x2222)

    assert bus.read16(0x7000, bank=1) == 0x1111
    assert bus.read16(0x7000, bank=2) == 0x2222


def test_disk_dma_latches_the_selected_bank(tmp_path):
    selected_bank = [1]
    bus = MemoryBus(lambda: selected_bank[0])
    image = tmp_path / "disk.img"
    image.write_bytes(b"\x34\x12" + bytes(SECTOR_WORDS * 2 - 2))
    disk = Disk(str(image), bus)
    disk.memory_address = 0x7000
    disk.execute_command(COMMAND_READ)

    selected_bank[0] = 2
    for _ in range(SECTOR_WORDS):
        disk.tick()

    assert bus.peek16(0x7000, bank=1) == 0x1234
    assert bus.peek16(0x7000, bank=2) == 0

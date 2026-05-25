"""Emulator unit tests: memory system, MMIO, and breakpoints.

These tests operate below the instruction level — they exercise the memory
model (ROM protection, banking, VRAM), MMIO write side-effects, and the
breakpoint mechanism directly on the Emulator object.
"""

import pytest

from jaide.constants import (
    BANK_WINDOW_START,
    MMIO_SYSTEM,
    VRAM_START,
)
from jaide.exceptions import EmulatorException


class TestRomWriteProtection:

    def test_write_to_rom_is_silently_ignored(self, emu):
        # Pre-load a sentinel into ROM via the raw bytearray (bypassing write16)
        emu.memory[0x0050 * 2]     = 0xAB
        emu.memory[0x0050 * 2 + 1] = 0xCD
        original = emu.read16(0x0050)
        emu.write16(0x0050, 0x1234)  # should be silently ignored
        assert emu.read16(0x0050) == original  # unchanged

    def test_write_just_above_rom_succeeds(self, emu):
        # First word above the ROM guard is 0x0100
        emu.write16(0x0100, 0xBEEF)
        assert emu.read16(0x0100) == 0xBEEF

    def test_write_to_general_ram_succeeds(self, emu):
        emu.write16(0x2000, 0xCAFE)
        assert emu.read16(0x2000) == 0xCAFE


class TestMemoryBanking:

    def test_bank_isolates_data(self, emu):
        addr = BANK_WINDOW_START  # first word in the bank window

        emu.mb.set(1)
        emu.write16(addr, 0xAAAA)
        assert emu.read16(addr) == 0xAAAA

        # switch to bank 2 — should see zeros (fresh bank)
        emu.mb.set(2)
        assert emu.read16(addr) == 0
        emu.write16(addr, 0xBBBB)

        # switch back to bank 1 — original value must be intact
        emu.mb.set(1)
        assert emu.read16(addr) == 0xAAAA

    def test_bank_two_independent_of_bank_one(self, emu):
        addr = BANK_WINDOW_START + 0x10

        emu.mb.set(1)
        emu.write16(addr, 0x1111)
        emu.mb.set(2)
        emu.write16(addr, 0x2222)

        emu.mb.set(1)
        assert emu.read16(addr) == 0x1111
        emu.mb.set(2)
        assert emu.read16(addr) == 0x2222

    def test_mb_zero_uses_flat_memory(self, emu):
        # MB=0 means no banking; the window accesses the flat memory array.
        emu.mb.set(0)
        emu.write16(BANK_WINDOW_START, 0x5678)
        assert emu.read16(BANK_WINDOW_START) == 0x5678

        # switching to a bank should NOT expose the flat-memory value
        emu.mb.set(1)
        assert emu.read16(BANK_WINDOW_START) != 0x5678


class TestVramAccess:

    def test_vram_read_write(self, emu):
        emu.write16(VRAM_START + 0x100, 0xCAFE)
        assert emu.read16(VRAM_START + 0x100) == 0xCAFE

    def test_vram_backed_by_vram_buffer(self, emu):
        # VRAM_START word maps to vram[0] (byte offset 0)
        emu.write16(VRAM_START, 0x1234)
        assert emu.vram[0] == 0x34  # low byte (little-endian)
        assert emu.vram[1] == 0x12  # high byte

    def test_vram_does_not_alias_flat_memory(self, emu):
        # writes to VRAM go to emu.vram, not emu.memory
        emu.write16(VRAM_START + 0x200, 0xABCD)
        byte_offset = (VRAM_START + 0x200) * 2
        assert emu.memory[byte_offset]     == 0
        assert emu.memory[byte_offset + 1] == 0


class TestMmioWrite:

    def test_system_halt_command_sets_halted(self, assemble_and_load):
        emu = assemble_and_load(
            "mov A, 0xFEFF\n"   # MMIO_SYSTEM address
            "put [A], 0x0002\n" # halt command
            "nop\n"
        )
        emu.step()  # mov A
        emu.step()  # put [A], 0x0002 → emu.halted = True
        assert emu.halted

    def test_halted_emulator_raises_on_step(self, assemble_and_load):
        emu = assemble_and_load(
            "mov A, 0xFEFF\n"
            "put [A], 0x0002\n"
            "nop\n"
        )
        emu.step()
        emu.step()  # sets halted
        with pytest.raises(EmulatorException):
            emu.step()

    def test_unmapped_mmio_write_does_not_crash(self, emu):
        # writing to an unmapped MMIO address should be silently ignored
        emu.write16(0xFE20, 0x1234)  # no device registered at 0xFE20

    def test_mmio_write_direct(self, emu):
        # drive the method directly for the halt path
        assert not emu.halted
        emu.mmio_write(MMIO_SYSTEM, 0x0002)
        assert emu.halted


class TestBreakpoints:

    def test_breakpoint_raises_at_target_pc(self, assemble_and_load):
        emu = assemble_and_load("nop\nnop\nnop")
        emu.breakpoints.add(1)   # break when PC reaches 1
        emu.step()               # execute NOP at PC=0, PC → 1
        with pytest.raises(EmulatorException, match="breakpoint"):
            emu.step()           # PC=1 → breakpoint fires before execution

    def test_breakpoint_does_not_fire_at_other_pc(self, assemble_and_load):
        emu = assemble_and_load("nop\nnop\nnop")
        emu.breakpoints.add(10)  # far away
        emu.step()               # PC → 1, no raise
        assert emu.pc.value == 1

    def test_multiple_breakpoints(self, assemble_and_load):
        emu = assemble_and_load("nop\nnop\nnop\nnop")
        emu.breakpoints.add(1)
        emu.breakpoints.add(2)
        emu.step()  # PC → 1
        with pytest.raises(EmulatorException):
            emu.step()  # fires at PC=1
        # clear breakpoint 1 and continue to breakpoint 2
        emu.breakpoints.discard(1)
        emu.step()  # PC → 2
        with pytest.raises(EmulatorException):
            emu.step()  # fires at PC=2

    def test_remove_breakpoint_allows_execution(self, assemble_and_load):
        emu = assemble_and_load("nop\nnop\nnop")
        emu.breakpoints.add(1)
        emu.breakpoints.discard(1)  # remove before it fires
        emu.step()  # PC → 1, should NOT raise
        emu.step()  # PC → 2, should NOT raise
        assert emu.pc.value == 2

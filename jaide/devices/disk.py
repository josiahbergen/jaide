# device.py
# device base class for the jaide emulator.
# josiah bergen, march 2026

from typing import Callable

from ..util.logger import logger
from .device import Device

STATUS_IDLE = 0
STATUS_BUSY = 1
STATUS_ERROR = 2

COMMAND_READ = 0
COMMAND_WRITE = 1
SECTOR_WORDS = 256

class Disk(Device):
    def __init__(self, disk_file: str, read16: Callable[[int], int], write16: Callable[[int, int], None]):
        """Disk controller."""
        super().__init__()

        self.read16 = read16
        self.write16 = write16

        self.status = STATUS_IDLE
        self.sector_number = 0
        self.memory_address = 0
        self._command: int | None = None
        self._active_sector = 0
        self._active_memory_address = 0

        if not disk_file:
            logger.fatal("no image file provided!", scope="disk.py:Disk.__init__()")

        # hold the disk image in memory
        # fine, i guess. NOTE: optimize?
        self.disk_file = disk_file

        try:
            with open(self.disk_file, "rb") as f:
                self.disk = bytearray(f.read())
        except FileNotFoundError:
            logger.fatal(f"image file {self.disk_file} not found!", scope="disk.py:Disk.__init__()")

        # which word we are currently reading/writing to
        # simulates "slow" (non-instant) data transfer.
        # counts words.
        self._cursor = 0

        self.write_dispatch[0xFE20] = self.execute_command
        self.write_dispatch[0xFE21] = lambda value: setattr(self, "sector_number", value)
        self.write_dispatch[0xFE22] = lambda value: setattr(self, "memory_address", value)
        self.read_dispatch[0xFE23] = lambda: self.status

        self._log_ready()

    def _log_ready(self) -> None:
        logger.debug(f"device ready! {self.__class__.__name__} on {self._get_mmio_list()} (using {self.disk_file})")

    def execute_command(self, value: int) -> None:
        if self.status == STATUS_BUSY:
            # already doing something, ignore
            # TODO: add a command queue to handle stuff like this
            return

        if value not in (COMMAND_READ, COMMAND_WRITE):
            logger.warning(f"invalid disk command: 0x{value:02X}")
            self.status = STATUS_ERROR
            self._command = None
            return

        sector_start = self.sector_number * SECTOR_WORDS * 2
        if sector_start + SECTOR_WORDS * 2 > len(self.disk):
            logger.warning(f"disk sector {self.sector_number} is out of range")
            self.status = STATUS_ERROR
            self._command = None
            return

        if value == COMMAND_READ:
            logger.debug(f"got command: read sector {self.sector_number} to 0x{self.memory_address:04X}")
        else:
            logger.debug(f"got command: write sector {self.sector_number} from 0x{self.memory_address:04X}")

        self.status = STATUS_BUSY
        self._command = value
        self._active_sector = self.sector_number
        self._active_memory_address = self.memory_address
        self._cursor = 0

    def tick(self) -> None:
        if self.status != STATUS_BUSY or self._command is None:
            return

        disk_byte = (self._active_sector * SECTOR_WORDS + self._cursor) * 2
        memory_word = self._active_memory_address + self._cursor

        if self._command == COMMAND_READ:
            # kinda scuffed, but we have to parse out a little-endian value from the disk image
            # into a regular python int, and pass it into write16. which then converts it back to
            # a 16-bit little-endian value.
            value = (self.disk[disk_byte + 1] << 8) | self.disk[disk_byte]
            logger.verbose(f"reading word {self._cursor} of sector {self._active_sector} (0x{value:04X}) into 0x{memory_word:04X}")
            self.write16(memory_word, value)

        else:
            value = self.read16(memory_word)
            logger.verbose(f"writing 0x{value:04X} to word {self._cursor} of sector {self._active_sector}")
            self.disk[disk_byte : disk_byte + 2] = [value & 0xFF, (value >> 8) & 0xFF]

        self._cursor += 1
        if self._cursor == SECTOR_WORDS:
            self._complete_transfer()

    def _complete_transfer(self) -> None:
        logger.debug("transfer complete!")

        if self._command == COMMAND_WRITE:
            with open(self.disk_file, "wb") as f:
                f.write(self.disk)

        self.status = STATUS_IDLE
        self._command = None
        self._cursor = 0
        logger.debug("transfer complete! status reset to idle.")

    def reset(self) -> None:
        self.status = STATUS_IDLE
        self.sector_number = 0
        self.memory_address = 0
        self._command = None
        self._active_sector = 0
        self._active_memory_address = 0
        self._cursor = 0

    def __str__(self) -> str:
        return f"disk: status={self.status} sector={self.sector_number} address={self.memory_address}"

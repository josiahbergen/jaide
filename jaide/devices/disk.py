# device.py
# device base class for the jaide emulator.
# josiah bergen, march 2026

from ast import Return
from typing import Callable

from ..util.logger import logger
from .device import Device

PIT_INTERRUPT_VECTOR = 5

STATUS_IDLE = 0
STATUS_READING = 1
STATUS_WRITING = 2
STATUS_ERROR = 2

class Disk(Device):
    def __init__(self, irq: Callable[[int], None], disk_file: str, read16: Callable[[int], int], write16: Callable[[int, int], None]):
        """Disk controller."""
        super().__init__(irq)
        self.read16 = read16
        self.write16 = write16

        self.status = STATUS_IDLE
        self.sector_number = 0
        self.memory_address = 0

        # hold the disk image in memory
        # fine, i guess. NOTE: optimize?
        self.disk_file = disk_file
        self.disk = bytearray(open(self.disk_file, "rb").read())

        # which word we are currently reading/writing to
        # simulates "slow" (non-instant) data transfer.
        # counts words.
        self._cursor = 0

        self.write_dispatch[0x20] = self.execute_command
        self.write_dispatch[0x21] = lambda value: setattr(self, "sector_number", value)
        self.write_dispatch[0x22] = lambda value: setattr(self, "memory_address", value)
        self.read_dispatch[0x23] = lambda: self.status

        self._log_ready()

    def execute_command(self, value: int) -> None:
        if self.status in [STATUS_READING, STATUS_WRITING]:
            # already doing something, ignore
            # TODO: add a command queue to handle stuff like this
            return

        if value == 0x00: 
            logger.debug(f"got command: read sector {self.sector_number} to 0x{self.memory_address:04X}")
            self.status = STATUS_READING
            self._cursor = 0

        elif value == 0x01:
            logger.debug(f"got command: write sector {self.sector_number} from 0x{self.memory_address:04X}")
            self.status = STATUS_WRITING
            self._cursor = 0

        else: 
            logger.warning(f"invalid disk command: 0x{value:02X}")

    def tick(self) -> None:
        self._reset_if_done()

        if self.status == STATUS_READING:
            # kinda scuffed, but we have to parse out a little-endian value from the disk image
            # into a regular python int, and pass it into write16. which then converts it back to
            # a 16-bit little-endian value.
            value = (self.disk[self._cursor * 2 + 1] << 8) | self.disk[self._cursor * 2]
            logger.verbose(f"reading word {self._cursor} of sector {self.sector_number} (0x{value:04X}) into 0x{self.memory_address + self._cursor:04X}")
            self.write16(self.memory_address + self._cursor, value)
            self._cursor += 1

        if self.status == STATUS_WRITING:
            logger.verbose(f"writing 0x{self.read16(self.memory_address + self._cursor):04X} to disk (from 0x{self._cursor * 2:04X})")
            value = self.read16(self.memory_address + self._cursor)
            self.disk[self._cursor * 2 : self._cursor * 2 + 2] = [ value & 0xFF, (value >> 8) & 0xFF ]
            self._cursor += 1
        
    def _reset_if_done(self) -> None:
        if self._cursor < 256:  
            return 
         
        # raise interrupt vector 6 on transfer complete
        logger.debug(f"transfer complete! raising interrupt...")
        self.irq(6)

        # save modified disk image to the real file
        if self.status == STATUS_WRITING:
            with open(self.disk_file, "wb") as f:
                f.write(self.disk)

        self.status = STATUS_IDLE
        self._cursor = 0
        logger.debug(f"transfer complete! status reset to idle.")

    def __str__(self) -> str:
        return f"disk: status={self.status} sector={self.sector_number} address={self.memory_address}"

# device.py
# device base class for the jaide emulator.
# josiah bergen, march 2026

from typing import Callable

from ..exceptions import EmulatorException
from ..util.logger import logger


class Device:
    def __init__(self, irq: Callable[[int], None]):
        self.irq: Callable[[int], None] = irq

        # by default, no read or write handlers are defined
        self.read_dispatch: dict[int, Callable[..., int]] = {}
        self.write_dispatch: dict[int, Callable[[int], None]] = {}

    def mmio_read(self, addr: int) -> int:
        """Dispatch a request to read from a device."""

        read_handler = self.read_dispatch.get(addr)
        if read_handler is None:
            raise EmulatorException(f"{self.__class__.__name__} has no read handler for MMIO 0x{addr:04X}.")

        logger.debug(f"{self.__class__.__name__}: READ at MMIO 0x{addr:04X}...")
        return read_handler()

    def mmio_write(self, addr: int, value: int):
        """Dispatch a request to write to a device."""

        write_handler = self.write_dispatch.get(addr)
        if write_handler is None:
            raise EmulatorException(f"{self.__class__.__name__} has no write handler for MMIO 0x{addr:04X}.")

        logger.debug(f"{self.__class__.__name__}: WRITE to MMIO 0x{addr:04X} with 0x{value:04X}...")
        write_handler(value)

    def _get_mmio_list(self) -> str:
        """ return a string of format "0xFE01 (r/w), 0xFE02 (r), ..."
        """
        # [0] = read, [1] = write
        open_addrs: dict[int, list[bool]] = {}

        for addr, _ in self.read_dispatch.items():
            if addr not in open_addrs:
                open_addrs[addr] = [False, False]
            open_addrs[addr][0] = True
        for addr, _ in self.write_dispatch.items():
            if addr not in open_addrs:
                open_addrs[addr] = [False, False]
            open_addrs[addr][1] = True
        return ", ".join([
            f"0x{addr:04X} ({'r/w' if open_addrs[addr][0] and open_addrs[addr][1] else 'r' if open_addrs[addr][0] else 'w'})"
            for addr in open_addrs
        ])

    def tick(self) -> None:
        """Tick the device. Runs once per CPU cycle."""
        pass

    def _log_ready(self) -> None:
        logger.debug(f"device ready! {self.__class__.__name__} on {self._get_mmio_list()}")

    def __str__(self) -> str:
        return f"{self.__class__.__name__.lower()}: {self._get_mmio_list()}"

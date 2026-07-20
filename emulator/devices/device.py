# device.py
# device base class for the jaide emulator.
# josiah bergen, march 2026

from typing import Callable

from ..exceptions import EmulatorException
from ..util.logger import logger


class Device:
    def __init__(self):
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
        """ return a string of format "0xFE01 (r/w), 0xFE02 (r), ..."""
        return ", ".join(
            f"0x{addr:04X} ({'r/w' if r and w else 'r' if r else 'w'})"
            for addr in sorted(set(self.read_dispatch) | set(self.write_dispatch))
            for r, w in [(addr in self.read_dispatch, addr in self.write_dispatch)]
        )

    def tick(self) -> None:
        """Tick the device. Runs once per CPU cycle."""
        pass

    def reset(self) -> None:
        """Reset device state. Called by the emulator when reset asserted."""
        logger.warning(f"device {self.__class__.__name__} does not implement reset()")

    def _log_ready(self) -> None:
        logger.debug(f"device ready! {self.__class__.__name__} on {self._get_mmio_list()}")

    def __str__(self) -> str:
        return f"{self.__class__.__name__.lower()}: {self._get_mmio_list()}"

# device.py
# device base class for the jaide emulator.
# josiah bergen, march 2026

from typing import Callable

from .exceptions import EmulatorException
from .util.logger import logger


class Device:
    def __init__(self, irq: Callable[[int], None]):
        self.irq: Callable[[int], None] = irq

        # by default, no read or write handlers are defined
        self.read_dispatch: dict[int, Callable[..., int]] = {}
        self.write_dispatch: dict[int, Callable[[int], None]] = {}

    def port_read(self, port: int) -> int:
        """Dispatch a request to read from a device."""

        read_handler = self.read_dispatch.get(port)
        if read_handler is None:
            raise EmulatorException(f"no read handler for port {port} on {self.__class__.__name__}.")
        
        return read_handler()

    def port_write(self, port: int, value: int):
        """Dispatch a request to write to a device."""

        write_handler = self.write_dispatch.get(port)
        if write_handler is None:
            raise EmulatorException(f"no write handler for port {port} on {self.__class__.__name__}.")
        
        write_handler(value)

    def tick(self) -> None:
        """Tick the device. Runs once per CPU cycle."""
        pass

    def __str__(self) -> str:
        return f"generic device"

class PIT(Device):
    def __init__(self, irq: Callable[[int], None]):
        """Programmable interval timer."""
        super().__init__(irq)

        self.enabled: bool = False
        self.one_shot: bool = False
        self.counter: int = 0
        self.reload: int = 0xffff # arbitrary number for now

        # port 0x10:
        #   - read: get reload value
        #   - write: set reload value
        self.read_dispatch[0x10] = lambda: self.reload
        self.write_dispatch[0x10] = self.set_reload

        # port 0x11:
        #   - read: get reload value
        #   - write: set flags (enable bit, one-shot bit)
        self.read_dispatch[0x11] = lambda: self.reload
        self.write_dispatch[0x11] = self.set_flags

    def set_reload(self, value: int) -> None:
        self.reload = value

    def set_flags(self, value: int) -> None:
        self.enabled = (value & 0b00000001) != 0
        self.one_shot = (value & 0b00000010) != 0
        logger.debug(f"PIT flags set to {self.enabled}, {self.one_shot}")

    def tick(self) -> None:
        if not self.enabled:
            # device turned off, do nothing
            return
        self.counter -= 1

        if self.counter <= 0:
            if self.one_shot:
                self.enabled = False  # don't reset the counter in one-shot mode
            else:
                self.counter = self.reload  # run it back baby

            self.irq(5) # raise interrupt vector 5

    def __str__(self) -> str:
        return f"PIT: enabled={self.enabled}, one-shot={self.one_shot}, counter={self.counter}, reload={self.reload}"
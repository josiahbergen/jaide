# device.py
# device base class for the jaide emulator.
# josiah bergen, march 2026

from typing import Callable

from ..exceptions import EmulatorException


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

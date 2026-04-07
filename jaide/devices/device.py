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
        

    def port_read(self, port: int) -> int:
        """Dispatch a request to read from a device."""

        read_handler = self.read_dispatch.get(port)
        if read_handler is None:
            raise EmulatorException(f"{self.__class__.__name__} has no read handler for port {port}.")

        return read_handler()

    def port_write(self, port: int, value: int):
        """Dispatch a request to write to a device."""

        write_handler = self.write_dispatch.get(port)
        if write_handler is None:
            raise EmulatorException(f"{self.__class__.__name__} has no write handler for port {port}.")

        write_handler(value)

    def _get_port_list(self) -> str:
        """ return a string of format "port1 (r/w), port2 (r), ..."
        """
        # [0] = read, [1] = write
        open_ports: dict[int, list[bool]] = {}

        for port, _ in self.read_dispatch.items():
            if port not in open_ports:
                open_ports[port] = [False, False]
            open_ports[port][0] = True
        for port, _ in self.write_dispatch.items():
            if port not in open_ports:
                open_ports[port] = [False, False]
            open_ports[port][1] = True
        return ", ".join([f"0x{port:02X} ({'r/w' if open_ports[port][0] and open_ports[port][1] else 'r' if open_ports[port][0] else 'w'})" for port in open_ports])

    def tick(self) -> None:
        """Tick the device. Runs once per CPU cycle."""
        pass

    def _log_ready(self) -> None:
        logger.debug(f"device ready! {self.__class__.__name__} on {self._get_port_list()}")

    def __str__(self) -> str:
        return f"{self.__class__.__name__.lower()}: {self._get_port_list()}"

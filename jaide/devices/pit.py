# device.py
# device base class for the jaide emulator.
# josiah bergen, march 2026

from typing import Callable

from ..util.logger import logger
from .device import Device

PIT_INTERRUPT_VECTOR = 5

class PIT(Device):
    def __init__(self, irq: Callable[[int], None]):
        """Programmable interval timer."""
        super().__init__(irq)

        self.enabled: bool = False
        self.one_shot: bool = False
        self.counter: int = 0
        self.reload: int = 0xFFFF  # arbitrary number for now, gets set by set_reload

        self.read_dispatch[0x10]  = lambda: self.reload
        self.write_dispatch[0x10] = self._set_reload

        self.read_dispatch[0x11]  = self._get_flags
        self.write_dispatch[0x11] = self._set_flags

        logger.debug(f"pit device ready. ports open: {self._get_port_list()}")

    def _set_reload(self, value: int) -> None:
        self.reload = value

    def _set_flags(self, value: int) -> None:
        self.enabled = (value & 0b00000001) != 0
        self.one_shot = (value & 0b00000010) != 0
        logger.debug(f"pit flags set to enabled={self.enabled}, one-shot={self.one_shot}")

    def _get_flags(self) -> int:
        value = 0 | self.enabled
        value |= self.one_shot << 1
        return value

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

            self.irq(PIT_INTERRUPT_VECTOR)  # raise interrupt vector 5

    def __str__(self) -> str:
        return f"pit: enabled={self.enabled}, one-shot={self.one_shot}, counter={self.counter}, reload={self.reload}"

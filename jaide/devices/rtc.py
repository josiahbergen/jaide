# device.py
# device base class for the jaide emulator.
# josiah bergen, march 2026

import time
from re import T
from typing import Callable

from .device import Device


class RTC(Device):
    def __init__(self, irq: Callable[[int], None]):
        """Real-time clock."""
        super().__init__(irq)

        self.read_dispatch[0x30] = lambda: time.localtime().tm_sec
        self.read_dispatch[0x31] = lambda: time.localtime().tm_min
        self.read_dispatch[0x32] = lambda: time.localtime().tm_hour
        self.read_dispatch[0x33] = lambda: time.localtime().tm_yday

        self._log_ready()

    def tick(self) -> None:
        pass

    def __str__(self) -> str:
        t = time.localtime()
        return f"rtc: second={t.tm_sec}, minute={t.tm_min}, hour={t.tm_hour}, day_of_year={t.tm_yday}"

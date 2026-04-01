# device.py
# device base class for the jaide emulator.
# josiah bergen, march 2026

import time
from typing import Callable

from .device import Device


class RTC(Device):
    def __init__(self, irq: Callable[[int], None]):
        """Real-time clock."""
        super().__init__(irq)

        self.read_dispatch[0x30] = self.get_second
        self.read_dispatch[0x31] = self.get_minute
        self.read_dispatch[0x32] = self.get_hour
        self.read_dispatch[0x33] = self.get_day_of_year

    def get_second(self) -> int:
        return time.localtime().tm_sec

    def get_minute(self) -> int:
        return time.localtime().tm_min

    def get_hour(self) -> int:
        return time.localtime().tm_hour

    def get_day_of_year(self) -> int:
        return time.localtime().tm_yday

    def tick(self) -> None:
        pass

    def __str__(self) -> str:
        return f"rtc: second={self.get_second()}, minute={self.get_minute()}, hour={self.get_hour()}, day_of_year={self.get_day_of_year()}"

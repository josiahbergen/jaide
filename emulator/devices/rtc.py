# device.py
# device base class for the jaide emulator.
# josiah bergen, march 2026

import time

from .device import Device


class RTC(Device):
    def __init__(self):
        """Real-time clock."""
        super().__init__()

        self.read_dispatch[0xFE30] = lambda: time.localtime().tm_sec
        self.read_dispatch[0xFE31] = lambda: time.localtime().tm_min
        self.read_dispatch[0xFE32] = lambda: time.localtime().tm_hour
        self.read_dispatch[0xFE33] = lambda: time.localtime().tm_yday

        self._log_ready()

    def tick(self) -> None:
        pass

    def reset(self) -> None:
        pass

    def __str__(self) -> str:
        t = time.localtime()
        return f"rtc: second={t.tm_sec}, minute={t.tm_min}, hour={t.tm_hour}, day_of_year={t.tm_yday}"

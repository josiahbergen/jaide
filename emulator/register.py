# registers.py
# register utility class used by the emulator.
# josiah bergen, january 2026

from typing import Callable
from constants import USER_MODE

from exceptions import ProtectionFault


class Register:
    def __init__(self, name: str, value: int, execution_mode: Callable[[], int]):
        self.name: str = name
        self.value: int = 0
        self.execution_mode: Callable[[], int] = execution_mode
        self.set(value)

    # "intro to java" ahh methods

    def set(self, value: int) -> None:

        if self.name == "MB" and self.execution_mode() == USER_MODE:
            raise ProtectionFault(f"memory bank register cannot be set in user mode!")

        self.value = value & 0xFFFF  # mask to 16 bits

    def __str__(self) -> str:
        return f"{self.name}: 0x{self.value:04X}"

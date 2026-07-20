# registers.py
# register utility class used by the emulator.
# josiah bergen, january 2026


class Register:
    def __init__(self, name: str, value: int):
        self.name: str = name
        self.value: int = 0
        self.set(value)

    # "intro to java" ahh methods

    def set(self, value: int) -> None:
        self.value = value & 0xFFFF  # mask to 16 bits

    def __str__(self) -> str:
        return f"{self.name}: 0x{self.value:04X}"

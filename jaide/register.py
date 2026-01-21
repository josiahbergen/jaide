# registers.py
# register class used by the emulator.
# josiah bergen, january 2026

class Register:

    def __init__(self, name: str, value: int):
        self.name = name
        self.value = 0
        self.set(value)

    # java ahh setter

    def set(self, value: int) -> None:
        self.value = value & 0xFFFF # mask to 16 bits

    def __str__(self) -> str:
        return f"{self.name}: 0x{self.value:04X}"
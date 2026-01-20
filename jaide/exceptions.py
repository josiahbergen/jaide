# exceptions.py
# exceptions used by the emulator.
# josiah bergen, january 2026

class EmulatorException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


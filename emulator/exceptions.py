# exceptions.py
# exceptions used by the emulator.
# josiah bergen, january 2026

class EmulatorException(Exception):

    def __init__(self, message: str):
        self.message: str = message
        super().__init__(self.message)


    def __enter__(self):
        # pytest uses `with` to test exception calling,
        # so we need to implement __enter__ here
        return self

class ReplException(Exception):

    def __init__(self, message: str):
        self.message: str = message
        super().__init__(self.message)
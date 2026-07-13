# keyboard.py
# keyboard controller device for the jaide emulator.
# josiah bergen, april 2026

from collections import deque

from .device import Device


class Keyboard(Device):
    def __init__(self, key_queue: deque):
        """Keyboard controller. Reads translated scancodes from the shared queue populated by the graphics controller.

        key_queue -- shared deque[int] of scancodes pushed by Graphics
        """
        super().__init__()

        self._key_queue = key_queue
        self._pending: int  = 0      # scancode waiting to be read
        self._has_key: bool = False  # whether a key is ready

        self.read_dispatch[0xFE01] = self._read_key
        self.read_dispatch[0xFE02] = lambda: 0x01 if self._has_key else 0x00

        self._log_ready()

    def _read_key(self) -> int:
        """Return the pending scancode and clear it."""
        key = self._pending
        self._pending = 0
        self._has_key = False
        return key

    def tick(self) -> None:
        if self._has_key or not self._key_queue:
            return

        self._pending = self._key_queue.popleft()
        self._has_key = True

    def reset(self) -> None:
        self._key_queue.clear()
        self._pending = 0
        self._has_key = False

    def __str__(self) -> str:
        return f"keyboard: pending=0x{self._pending:02X}, has_key={self._has_key}"

"""Main-thread window events and rendering, independent of emulated devices."""

import time
from typing import Callable

import pygame
from pygame._sdl2 import Window

from .bus import MemoryBus
from .devices.graphics import Graphics
from .memory_view import MemoryView

FRAME_INTERVAL = 1 / 30


class EmulatorUI:
    def __init__(self, bus: MemoryBus, graphics: Graphics | None, memory_view: bool, shutdown: Callable[[], None]):
        pygame.init()
        self.graphics = graphics
        self.graphics_window = Window.from_display_module() if graphics else None
        self.memory_view = MemoryView(bus) if memory_view else None
        self.shutdown = shutdown
        self._last_frame = 0.0

    def tick(self) -> None:
        if self.graphics is None and self.memory_view is None:
            return
        now = time.monotonic()
        if now - self._last_frame < FRAME_INTERVAL:
            return
        self._last_frame = now

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # SDL also sends QUIT after closing its last window. Closing a
                # standalone memory viewer should leave the terminal running.
                if self.graphics is not None or self.memory_view is not None:
                    self.shutdown()
                return
            window = getattr(event, "window", None)
            if self.memory_view is not None and window == self.memory_view.window:
                if event.type == pygame.WINDOWCLOSE:
                    self.memory_view.close()
                    self.memory_view = None
                else:
                    self.memory_view.handle_event(event)
            elif self.graphics is not None and window == self.graphics_window:
                if event.type == pygame.WINDOWCLOSE:
                    self.shutdown()
                    return
                self.graphics.handle_event(event)

        if self.graphics is not None:
            self.graphics.draw()
        if self.memory_view is not None:
            self.memory_view.draw(now)

    def close(self) -> None:
        if self.memory_view is not None:
            self.memory_view.close()
            self.memory_view = None
        pygame.quit()

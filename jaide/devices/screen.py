import tkinter as tk
from PIL import Image, ImageTk

WIDTH  = 128
HEIGHT = 64      # 128 * 64 = 8192 words
SCALE  = 5
FPS_MS = 33      # ~30 FPS


class Screen:
    def __init__(self, vram: memoryview):
        self.vram = vram
        self.framebuf = bytearray(WIDTH * HEIGHT)  # 1 byte per pixel
        self._last_hash = None

        self.root = tk.Tk()
        self.root.title("jaide video output")
        self.root.geometry(f"{WIDTH * SCALE}x{HEIGHT * SCALE}")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.label = tk.Label(self.root, bg="black")
        self.label.pack()

        self.photo = None
        self._tick()

    def _render(self):
        mem = self.vram
        out = self.framebuf

        # word-addressed: 2 bytes per pixel
        j = 0
        for i in range(0, WIDTH * HEIGHT * 2, 2):
            out[j] = 0 if mem[i] | (mem[i + 1]  << 8) == 0 else 255
            j += 1

    def _tick(self):
        self._render()
        h = hash(bytes(self.framebuf))

        if h != self._last_hash:
            self._last_hash = h
            img = Image.frombuffer("L", (WIDTH, HEIGHT), bytes(self.framebuf), "raw", "L", 0, 1)
            img = img.resize((WIDTH * SCALE, HEIGHT * SCALE), Image.Resampling.NEAREST)

            self.photo = ImageTk.PhotoImage(img)
            self.label.configure(image=self.photo)

        self.root.after(FPS_MS, self._tick)

    def close(self):
        self.root.destroy()

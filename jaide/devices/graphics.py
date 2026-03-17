import tkinter as tk
from PIL import Image, ImageTk
from multiprocessing import Process

from ..emulator import Emulator

WIDTH  = 80
HEIGHT = 25
GLYPH_WIDTH = 8
GLYPH_HEIGHT = 16
FPS_MS = 33

COLORS = [
    (0, 0, 0),       # 0: black
    (255, 255, 255), # 1: white
    (255, 0, 0),     # 2: red
    (0, 255, 0),     # 3: green
    (0, 0, 255),     # 4: blue
    (255, 255, 0),   # 5: yellow
    (0, 255, 255),   # 6: cyan
    (255, 0, 255),   # 7: purple
    (128, 128, 128), # 8: gray
    (192, 192, 192), # 9: light gray
    (128, 0, 0),     # 10: dark red
    (0, 128, 0),     # 11: dark green
    (0, 0, 128),     # 12: dark blue
    (128, 128, 0),   # 13: dark yellow
    (0, 128, 128),   # 14: dark cyan
    (128, 0, 128),   # 15: dark magenta
]

class Graphics(Process):

    def __init__(self, emulator: Emulator, vram: sharedmemory):

        super().__init__(daemon=True)
        self.vram: memoryview = vram # memoryview of vram
        self.emulator: Emulator = emulator # emulator instance

        # load glyphs before the thread starts
        # ideally we would pass in glyphs as a bytearray or something
        try:
            with open("jaide/devices/VGA8.F16", "rb") as f:
                self.glyphs = [bytes(f.read(16)) for _ in range(256)]
        except FileNotFoundError:
            print("graphics: VGA8.F16 not found")
            return

        print("graphics ready.")


    def run(self):
        # runs in the graphics thread. all tk stuff lives here.
        self.root = tk.Tk()
        self.root.title("jaide video controller output")
        self.root.geometry(f"{WIDTH * GLYPH_WIDTH}x{HEIGHT * GLYPH_HEIGHT}")

        self.framebuf = [0] * (WIDTH * GLYPH_WIDTH * HEIGHT * GLYPH_HEIGHT * 3)
        self.label = tk.Label(self.root, bg="black")  # what we render the framebuffer to
        self.label.pack()

        self.root.bind("<Key>", self.on_key)
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)  # disable close button

        self.last_hash = None
        self.photo = None
        self.closed = False
        self._after_callback = None

        self.render()  # schedules next render via after(); mainloop() processes them
        self.root.mainloop() # TODO: what does this do?


    def on_key(self, event):
        if event.char:
                self.emulator.ports[1] = ord(event.char) # send key to port 1
                self.emulator.request_interrupt(4) # send keyboard interrupt

    def close(self):
        self.closed = True
        if self._after_callback is not None:
            # cancel any scheduled render callback to prevent tkinter from
            # attempting to render after the window is destroyed
            self.root.after_cancel(self._after_callback)
            self._after_callback = None

        # destroy the window and shutdown the emulator
        self.root.destroy()
        self.emulator.shutdown()

    def render(self):


        def parse_attrs(byte: int):
            fore = byte & 0b1111
            back = (byte >> 4) & 0b1111
            return (COLORS[fore], COLORS[back])

        def draw_glyph(glyph: bytes, fore, back, char_row, char_col):
            base_y = char_row * GLYPH_HEIGHT
            base_x = char_col * GLYPH_WIDTH

            for y in range(GLYPH_HEIGHT):
                row_byte = glyph[y]
                for x in range(GLYPH_WIDTH):
                    bit = (row_byte >> (GLYPH_WIDTH - 1 - x)) & 1
                    color = fore if bit else back
                    pixel_idx = ((base_y + y) * WIDTH * GLYPH_WIDTH + (base_x + x)) * 3
                    self.framebuf[pixel_idx + 0] = color[0]
                    self.framebuf[pixel_idx + 1] = color[1]
                    self.framebuf[pixel_idx + 2] = color[2]

        if self.closed:
            return

        # hash to check if vram changed
        current_data = bytes(self.vram[:WIDTH * HEIGHT * 2]) # read only relevant part
        h = hash(current_data)
        
        if h != self.last_hash:
            self.last_hash = h
            
            # main render to framebuffer
            for char_idx in range(WIDTH * HEIGHT):
                i = char_idx * 2
                lo, hi = self.vram[i], self.vram[i + 1]
                fore, back = parse_attrs(hi)
                draw_glyph(self.glyphs[lo], fore, back, char_idx // WIDTH, char_idx % WIDTH)
            
            # convert framebuffer to image to display in the window
            img = Image.frombuffer("RGB", (WIDTH * GLYPH_WIDTH, HEIGHT * GLYPH_HEIGHT), bytes(self.framebuf), "raw")
            self.photo = ImageTk.PhotoImage(img)
            self.label.configure(image=self.photo)

        if not self.closed:
            # schedule next render
            # we save the id here so we can cancel it on close
            self._after_callback = self.root.after(FPS_MS, self.render)


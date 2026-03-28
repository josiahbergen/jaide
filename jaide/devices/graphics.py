import tkinter as tk
import os
from PIL import Image, ImageTk
from multiprocessing import Process, shared_memory

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


def _load_glyphs() -> list[bytes]:
    try:
        with open("jaide/devices/VGA8.F16", "rb") as f:
            return [bytes(f.read(16)) for _ in range(256)]
    except FileNotFoundError:
        print("graphics: VGA8.F16 not found")
        return []


def graphics_main(vram_name: str, vram_size: int, key_queue, stop_event) -> None:
    """Entry point for the graphics process."""

    glyphs = _load_glyphs()
    if not glyphs:
        return

    shm = shared_memory.SharedMemory(name=vram_name)
    vram = memoryview(shm.buf)[:vram_size]

    root = tk.Tk()
    root.title("jaide video controller output")
    root.geometry(f"{WIDTH * GLYPH_WIDTH}x{HEIGHT * GLYPH_HEIGHT}")

    framebuf = [0] * (WIDTH * GLYPH_WIDTH * HEIGHT * GLYPH_HEIGHT * 3)
    blink_timer = 0
    label = tk.Label(root, bg="black")
    label.pack()

    last_hash = None
    photo = None

    def on_key(event):
        if event.char:
            key_queue.put(ord(event.char))

    root.bind("<Key>", on_key)
    root.protocol("WM_DELETE_WINDOW", lambda: stop_event.set())

    def parse_attrs(byte: int) -> tuple[tuple[int, int, int], tuple[int, int, int], bool]:
        # doc/graphics.md: attrs byte is `FFFF BBB B`
        fore = byte & 0b1111
        back = (byte >> 4) & 0b111
        blink = bool((byte >> 7) & 0b1)
        return (COLORS[fore], COLORS[back], blink)

    def draw_glyph(glyph: bytes, attrs, blink_on, char_row, char_col):
        base_y = char_row * GLYPH_HEIGHT
        base_x = char_col * GLYPH_WIDTH
        fore, back, blink = attrs
        
        if blink and blink_on: # swap fore/back if blink is on
            fore, back = back, fore

        for y in range(GLYPH_HEIGHT):
            row_byte = glyph[y]
            for x in range(GLYPH_WIDTH):
                bit = (row_byte >> (GLYPH_WIDTH - 1 - x)) & 1
                color = fore if bit else back
                pixel_idx = ((base_y + y) * WIDTH * GLYPH_WIDTH + (base_x + x)) * 3
                framebuf[pixel_idx + 0] = color[0]
                framebuf[pixel_idx + 1] = color[1]
                framebuf[pixel_idx + 2] = color[2]

    def render():
        nonlocal last_hash, photo, blink_timer

        if stop_event.is_set():
            root.destroy()
            try:
                vram.release()
            except Exception:
                pass
            shm.close()
            return

        blink_timer = (blink_timer + 1) % 8
        blink_on = blink_timer < 4

        current_data = bytes(vram[:WIDTH * HEIGHT * 2])  # read only relevant part
        h = hash(current_data + bytes([1 if blink_on else 0]))

        if h != last_hash:
            last_hash = h

            # main render to framebuffer
            for char_idx in range(WIDTH * HEIGHT):
                i = char_idx * 2
                lo, hi = vram[i], vram[i + 1]
                attrs = parse_attrs(hi)

                draw_glyph(glyphs[lo], attrs, blink_on, char_idx // WIDTH, char_idx % WIDTH)

            # convert framebuffer to image to display in the window
            img = Image.frombuffer(
                "RGB",
                (WIDTH * GLYPH_WIDTH, HEIGHT * GLYPH_HEIGHT),
                bytes(framebuf),
                "raw",
            )
            photo = ImageTk.PhotoImage(img)
            label.configure(image=photo)

        root.after(FPS_MS, render)

    render()
    root.mainloop()


def start_graphics_process(vram_name: str, vram_size: int, key_queue, stop_event) -> Process:
    """Helper to spawn the graphics process."""
    proc = Process(
        target=graphics_main,
        args=(vram_name, vram_size, key_queue, stop_event),
        daemon=True,
    )
    proc.start()
    return proc


import tkinter as tk

class Screen:
    def __init__(self, width: int=800, height: int=600):
        self.root = tk.Tk()
        self.root.title("rgb screen for the jaide computing system")
        self.root.geometry(f"{width}x{height}")
        self.canvas = tk.Canvas(self.root, width=width, height=height, bg="black")
        self.canvas.pack()

        self.pixels_on = True
        self._blink_pixels()
        self.root.mainloop()

    def _blink_pixels(self):
        if self.pixels_on:
            self.canvas.create_rectangle(0, 0, 10, 20, fill="white") 
        else:
            self.clear()
        
        self.pixels_on = not self.pixels_on
        self.root.after(500, self._blink_pixels)

    def draw_pixel(self, x: int, y: int, color: str):
        self.canvas.create_rectangle(x * 10, y * 10, (x + 1) * 10, (y + 1) * 10, fill=color)

    def clear(self):
        self.canvas.delete("all")

    def close(self):
        self.root.destroy()
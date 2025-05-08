import tkinter as tk
from PIL import Image, ImageTk

def on_click(event):
    x, y = event.x, event.y
    print(f"Clicked at: ({x}, {y})")

def open_image_window(image_path):
    root = tk.Tk()
    root.title("Click on the Image")

    # Load image with PIL
    pil_image = Image.open(image_path)
    tk_image = ImageTk.PhotoImage(pil_image)

    # Create a canvas and display the image
    canvas = tk.Canvas(root, width=pil_image.width, height=pil_image.height)
    canvas.pack()
    canvas.create_image(0, 0, anchor="nw", image=tk_image)

    # Bind click event
    canvas.bind("<Button-1>", on_click)

    root.mainloop()

# Example usage
open_image_window("images/screenshot.jpg")

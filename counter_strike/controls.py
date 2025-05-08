from typing import List
from e2b_desktop import Sandbox


def execute_mouse_movements(mouse_movements: List, desktop: "Sandbox"):
    for i, move_coords in enumerate(mouse_movements):
        print(f"Aiming to coords {i+1}: {move_coords}")
        desktop.move_mouse(**move_coords)
    print("-" * 30)

def shoot(desktop: "Sandbox", clicks: int = 3):
    for i in range(clicks):
        desktop.left_click()
        desktop.wait(200)
        desktop.left_click()
        desktop.wait(200)
        desktop.left_click()
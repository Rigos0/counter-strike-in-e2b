import base64
from e2b_desktop import Sandbox
from PIL import Image, ImageDraw, ImageFont

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def get_screenshot(desktop: Sandbox, filename = "screenshot.jpg"):
    image_bytes = desktop.screenshot(format="bytes")

    if filename:
        with open(filename, "wb") as f:
            f.write(image_bytes)

    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    return base64_image


def get_screenshot_message(desktop: Sandbox, filename: str | None = None):
    base64_image = get_screenshot(desktop, filename)
    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                    },
                },
            ], }
    ]

def draw_point(point, image_path, output_path,
               marker_radius=5, marker_color='red'):
    """
    Draw a circle at the given point and save the image.

    Args:
        point (dict): {'x': int, 'y': int}
        image_path (str): Path to the input image.
        output_path (str): Where to save the annotated image.
        marker_radius (int): Radius of the point marker.
        marker_color (str): Color for the marker and label background.
    """
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    x, y = point['x'], point['y']

    # Draw circle marker
    draw.ellipse(
        [(x - marker_radius, y - marker_radius),
         (x + marker_radius, y + marker_radius)],
        outline=marker_color,
        width=2
    )

    # Optionally label the point with its coordinates
    label = f"({x}, {y})"
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = x - text_w // 2
    text_y = y + marker_radius + 2

    draw.rectangle(
        [text_x, text_y, text_x + text_w, text_y + text_h],
        fill=marker_color
    )
    draw.text((text_x, text_y), label, fill='white', font=font)

    img.save(output_path)


#--------------------------------------------AIMING---------------------------------------------#
def calculate_aim_destination_1d(current_pos, center_pos, multiplier):
    """
    Calculates the destination coordinate along one axis based on aiming logic.

    Args:
        current_pos (float): The current coordinate of the mouse/object on the axis.
        center_pos (float): The center coordinate of the screen on the axis.
        multiplier (float): The aim multiplier.

    Returns:
        float: The calculated new coordinate on the axis.
    """
    if current_pos >= center_pos:
        diff = current_pos - center_pos
        return center_pos + diff * multiplier
    else:  # Aiming towards the origin from the center
        diff = center_pos - current_pos
        return center_pos - diff * multiplier

def calculate_mouse_movements(screenshot_coords, x_mid, y_mid, aim_multiplier, screen_width, screen_height):
    """
    Calculates new mouse position(s) based on screenshot coordinates and screen center,
    handling screen boundary overflows by potentially splitting the movement into two.

    Args:
        screenshot_coords (tuple): A tuple (scr_x, scr_y) of the detected coordinates.
        x_mid (float): The x-coordinate of the screen center.
        y_mid (float): The y-coordinate of the screen center.
        aim_multiplier (float): The multiplier to apply to the aim.
        screen_width (float): The total width of the screen.
        screen_height (float): The total height of the screen.

    Returns:
        list: A list of dictionaries, where each dictionary is {"x": int, "y": int}
              representing a mouse movement to absolute coordinates.
    """
    scr_x, scr_y = screenshot_coords
    movements = []

    ideal_new_x = calculate_aim_destination_1d(scr_x, x_mid, aim_multiplier)
    ideal_new_y = calculate_aim_destination_1d(scr_y, y_mid, aim_multiplier)

    is_ideal_x_out_of_bounds = ideal_new_x > screen_width or ideal_new_x < 0
    is_ideal_y_out_of_bounds = ideal_new_y > screen_height or ideal_new_y < 0

    if not is_ideal_x_out_of_bounds and not is_ideal_y_out_of_bounds:
        # Target is within bounds, single movement.
        movements.append({"x": int(ideal_new_x), "y": int(ideal_new_y)})
    else:
        # Target is out of bounds, potentially split into two movements.
        # First movement: Move to the screen edge, adjusting the secondary axis.
        actual_first_move_x = ideal_new_x
        actual_first_move_y = ideal_new_y
        
        x_hit_edge = False
        if ideal_new_x > screen_width:
            actual_first_move_x = screen_width
            x_hit_edge = True
        elif ideal_new_x < 0:
            actual_first_move_x = 0
            x_hit_edge = True

        y_hit_edge = False
        if ideal_new_y > screen_height:
            actual_first_move_y = screen_height
            y_hit_edge = True
        elif ideal_new_y < 0:
            actual_first_move_y = 0
            y_hit_edge = True
        
        # If one axis hits an edge, clamp the other axis's movement for the first step
        # to maintain the intended direction as much as possible.
        if x_hit_edge and not y_hit_edge: # X hit edge, Y is along for the ride (clamped)
            actual_first_move_y = max(0, min(ideal_new_y, screen_height))
        elif y_hit_edge and not x_hit_edge: # Y hit edge, X is along for the ride (clamped)
            actual_first_move_x = max(0, min(ideal_new_x, screen_width))
        # If both hit edges, actual_first_move_x and actual_first_move_y are already at a corner.

        movements.append({"x": int(actual_first_move_x), "y": int(actual_first_move_y)})

        # Second movement: If the first move was clamped, calculate the remaining "aim intention"
        # and apply it from the screen center for the second move.
        remaining_x_vector = ideal_new_x - actual_first_move_x
        remaining_y_vector = ideal_new_y - actual_first_move_y

        if remaining_x_vector != 0 or remaining_y_vector != 0:
            # The target for the second move is the screen center plus the remaining vector.
            second_target_x = x_mid + remaining_x_vector
            second_target_y = y_mid + remaining_y_vector

            final_second_move_x = max(0, min(second_target_x, screen_width))
            final_second_move_y = max(0, min(second_target_y, screen_height))
            
            movements.append({"x": int(final_second_move_x), "y": int(final_second_move_y)})
            
    return movements

def aim_to_position(coords: Dict[str, float]):
    """Aims and moves the mouse towards a target derived from input coordinates."""
    scr_x = coords["x"]
    scr_y = coords["y"]
    screenshot_coords = (scr_x, scr_y)

    # Default screen/aim parameters (could be made configurable)
    x_mid = 960.0
    y_mid = 540.0
    aim_multiplier = 1.3

    # Determine screen dimensions (assuming mid is indeed the center)
    screen_width = x_mid * 2
    screen_height = y_mid * 2

    # Get the list of movements
    planned_movements = calculate_mouse_movements(
        screenshot_coords,
        x_mid,
        y_mid,
        aim_multiplier,
        screen_width,
        screen_height
    )

    # Execute the movements
    print(f"Aiming based on input coords: {coords}")
    if not planned_movements:
        print("No movement calculated.")
    else:
        for i, move_coords in enumerate(planned_movements):
            print(f"Aiming to coords {i+1}: {move_coords}")
            desktop.move_mouse(**move_coords)
    print("-" * 30)




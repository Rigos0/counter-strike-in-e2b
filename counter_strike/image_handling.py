import base64
from e2b_desktop import Sandbox
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, List, Tuple
import io
from io import BytesIO


def encode_image(image_path: str):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")
        

def save_image(image_bytes: bytes, filename: str):
    with open(filename, "wb") as f:
        f.write(image_bytes)


def compress_image_bytes(image_bytes: bytes, quality=70) -> bytes:
    image = Image.open(BytesIO(image_bytes))
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


def encode_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def capture_screenshot_bytes(desktop) -> bytes:
    return desktop.screenshot(format="bytes")


def get_screenshot(desktop, filename="screenshot.jpg", quality: int = None) -> str:
    raw_bytes = capture_screenshot_bytes(desktop=desktop)

    if quality:
        raw_bytes = compress_image_bytes(raw_bytes, quality=quality) 

    if filename:
        save_image(raw_bytes, filename)

    return base64.b64encode(raw_bytes).decode("utf-8")

def get_screenshot_message_from_base64(base64_image):
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

def get_screenshot_message(desktop: Sandbox, filename: str | None = None, quality: int = None):
    base64_image = get_screenshot(desktop, filename=filename, quality=quality)
    screenshot_message = get_screenshot_message_from_base64(base64_image)
    return screenshot_message, base64_image

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


def get_mouse_movements(coords: Dict[str, float]):
    """Get list of mouse movements towards a target derived from input coordinates."""
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

    return planned_movements

RESAMPLE_METHOD = Image.Resampling.LANCZOS

def compress_and_scale_base64_image(base64_string, target_size_percentage=50, scale_percentage=50):
    if not base64_string: return None
    # Ensure percentages are within a valid range for the operation's intent
    if not (1 <= target_size_percentage <= 100): return None
    if not (1 <= scale_percentage <= 100): return None

    img_data = base64.b64decode(base64_string)
    original_size_bytes = len(img_data)
    target_size_bytes = original_size_bytes * target_size_percentage / 100

    img = Image.open(io.BytesIO(img_data))
    original_width, original_height = img.size

    if scale_percentage < 100:
        new_width = max(1, int(original_width * scale_percentage / 100))
        new_height = max(1, int(original_height * scale_percentage / 100))
        if (new_width, new_height) != (original_width, original_height):
             img = img.resize((new_width, new_height), RESAMPLE_METHOD)

    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        background = Image.new('RGB', img.size, (255, 255, 255))
        converted_img = img.convert('RGBA')
        if converted_img.mode == 'RGBA':
             mask = converted_img.split()[-1]
             background.paste(converted_img, (0, 0), mask=mask)
             img = background
        else:
             img = img.convert('RGB')
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    buffer_q95 = io.BytesIO()
    img.save(buffer_q95, format="JPEG", quality=95, optimize=True)
    data_q95 = buffer_q95.getvalue()

    if target_size_percentage == 100:
         return base64.b64encode(data_q95).decode('utf-8')

    if len(data_q95) <= target_size_bytes:
        return base64.b64encode(data_q95).decode('utf-8')

    best_data_under_target = None
    lowest_quality_data = None

    buffer_q1 = io.BytesIO()
    img.save(buffer_q1, format="JPEG", quality=1, optimize=True)
    lowest_quality_data = buffer_q1.getvalue()

    quality_min, quality_max = 1, 95
    for _ in range(8):
        if quality_min > quality_max: break

        current_quality = (quality_min + quality_max) // 2
        if current_quality < 1: current_quality = 1

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=current_quality, optimize=True)
        current_data = buffer.getvalue()
        current_size = len(current_data)

        if current_size <= target_size_bytes:
            best_data_under_target = current_data
            quality_min = current_quality + 1
        else:
            quality_max = current_quality - 1

    if best_data_under_target is not None:
        final_data = best_data_under_target
    else:
        final_data = lowest_quality_data

    final_base64 = base64.b64encode(final_data).decode('utf-8')
    return final_base64
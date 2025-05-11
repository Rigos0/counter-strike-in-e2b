"""
run_agent() is the main function which is getting imported from here
"""

import concurrent.futures
import time 
from e2b_desktop import Sandbox

from llms.models import OpenRouterGameplayModel, AimingModel

from .controls import aim, shoot
from .image_handling import draw_point, get_screenshot_message, get_mouse_movements
from .image_logging import ImageLoggingSettings
from .prompts import T_AIMING_PROMPT, CT_AIMING_PROMPT


class AgentSettings:
    def __init__(self,
                 side: str,
                 open_router_api_key_name: str = "OPENROUTER_API_KEY",
                 wait_on_start: int = 0
                 ):
        """
        :param side: 'CT' or 'T'
        """
        
        self.open_router_key_name = open_router_api_key_name
        if side == "CT":
            self.aiming_system_prompt = CT_AIMING_PROMPT
            self.team_choice = "2"
            self.skin_choice = "3"
        elif side == "T":
            self.aiming_system_prompt = T_AIMING_PROMPT
            self.team_choice = "1"
            self.skin_choice = "4"
        else:
            raise ValueError("Please choose a valid side from ['CT', 'T'].")


def run_model_async(executor, model, message):
    return executor.submit(model.complete, user_messages=message)


def get_aiming_result(future_aiming, aiming_model):
    time_start = time.perf_counter()
    point_json, _ = future_aiming.result()
    time_end = time.perf_counter()
    coords = aiming_model.parse_point_json(point_json)
    elapsed = time_end - time_start
    return coords, elapsed


def handle_gameplay_model_response(future_gameplay, coords_found):
    tool_calls_output = None
    gameplay_model_time = 0

    if coords_found:
        if not future_gameplay.done():
            future_gameplay.cancel()
        else:
            try:
                future_gameplay.result(timeout=0.01)
            except (concurrent.futures.TimeoutError, concurrent.futures.CancelledError):
                pass
    else:
        time_start = time.perf_counter()
        _, _, tool_calls_output = future_gameplay.result()
        time_end = time.perf_counter()
        gameplay_model_time = time_end - time_start

    return tool_calls_output, gameplay_model_time


def process_models_concurrently(screenshot_message, aiming_model, gameplay_model):
    """
    Runs aiming and gameplay models concurrently, prioritizing aiming results.
    Returns coordinates if found, otherwise tool_calls from gameplay.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_aiming = run_model_async(executor, aiming_model, screenshot_message)
        future_gameplay = run_model_async(executor, gameplay_model, screenshot_message)

        coords, aiming_model_time = get_aiming_result(future_aiming, aiming_model)
        tool_calls_output, gameplay_model_time = handle_gameplay_model_response(future_gameplay, coords)

    return coords, tool_calls_output, aiming_model_time, gameplay_model_time


def perform_aiming_sequence(coords, desktop, image_log_settings: ImageLoggingSettings):
    """
    Executes the sequence of actions when coordinates are available.
    """
    # print(f"Coordinates found: {coords}. Proceeding with aiming and shooting.") # Less verbose
    draw_point(point=coords, 
               image_path=image_log_settings.get_screenshot_path(), 
               output_path=image_log_settings.get_annotated_screenshot_path())
    mouse_movements = get_mouse_movements(coords=coords)
    aim(mouse_movements, desktop=desktop)
    shoot(desktop=desktop)


def handle_gameplay_actions(tool_calls, gameplay_model_instance): # Added gameplay_model_instance
    """
    Handles the actions based on tool_calls from the gameplay model.
    """
    if tool_calls:
        # print(f"No coordinates. Using tool_calls: {tool_calls}") # Less verbose
        gameplay_model_instance._handle_tool_calls(tool_calls=tool_calls)

    else:
        print("No coordinates found and no tool calls to execute from gameplay model.")


def capture_screenshot(desktop, image_logger):
    start_time = time.perf_counter()
    screenshot_path = image_logger.generate_new_paths_for_iteration()
    screenshot_message = get_screenshot_message(desktop, filename=screenshot_path)
    elapsed_time = time.perf_counter() - start_time
    print(f"  [Time] Screenshot: {elapsed_time:.4f}s")
    return screenshot_message


def decide_and_act(coords, tool_calls, gameplay_time, desktop, image_logger, gameplay_model):
    if coords:
        print(f"  [Action] Coords found: {coords}. Aiming & Shooting.")
        perform_aiming_sequence(coords, desktop, image_logger)
        return "Aim & Shoot"
    
    if tool_calls:
        print(f"  [Action] No Coords. Using Gameplay Model Tool Calls.")
        if gameplay_time > 0:
            print(f"  [Time] Gameplay Model: {gameplay_time:.4f}s")
        handle_gameplay_actions(tool_calls, gameplay_model)
        return f"Tool Calls: {tool_calls}"
    
    print(f"  [Action] No Coords, No Tool Calls.")
    if gameplay_time > 0:
        print(f"  [Time] Gameplay Model (no valid output): {gameplay_time:.4f}s")
    return "No Action"

def run_agent(aiming_model: AimingModel,
              gameplay_model: OpenRouterGameplayModel, 
              desktop: Sandbox, 
              iterations:int =10):
    
    image_logger = ImageLoggingSettings(base_path="images")

    for i in range(iterations):
        print(f"\n--- Iteration {i + 1} ---")
        iteration_start = time.perf_counter()

        screenshot_message = capture_screenshot(desktop, image_logger)

        coords, tool_calls, aiming_time, gameplay_time = process_models_concurrently(
            screenshot_message,
            aiming_model,
            gameplay_model
        )
        print(f"  [Time] Aiming Model: {aiming_time:.4f}s")

        action_taken = decide_and_act(
            coords, tool_calls, gameplay_time, desktop, image_logger, gameplay_model
        )

        iteration_end = time.perf_counter()
        print(f" Action taken: {action_taken}")
        print(f"  [Time] Iteration {i+1} Total: {iteration_end - iteration_start:.4f}s")
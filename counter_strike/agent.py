"""
run_agent() is the main function which is getting imported from here
"""

import concurrent.futures
import time 
from e2b_desktop import Sandbox
import collections
import copy
from typing import List, Dict

from llms.models import OpenRouterGameplayModel, AimingModel

from .controls import aim, shoot
from .image_handling import draw_point, get_screenshot_message, get_screenshot_message_from_base64, \
    get_mouse_movements, compress_and_scale_base64_image
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
        
        
class AgentMemory:
    def __init__(self, max_iterations=3):
        self.iterations = collections.deque(maxlen=max_iterations)

    def add_iteration(self, action_message: List[Dict], screenshot_message: List[Dict]):
        new_iteration = [action_message, screenshot_message]
        self.iterations.append(new_iteration)

    def get_memory_as_messages(self):
        all_messages = []
        for iteration in self.iterations:
            action_messages, screenshot_messages = iteration
            all_messages.extend(action_messages)
            all_messages.extend(screenshot_messages)
        return all_messages

    def print_memory(self):
        print("\nMemory:")
        for i, iteration in enumerate(self.iterations):
            print(f"Iteration {i + 1}")
            for message_list in iteration:
                # Ensure message_list is iterable (i.e., a list of dicts)
                if isinstance(message_list, list):
                    for message in message_list:
                        if isinstance(message, dict):
                            role = message.get('role', 'unknown')
                            content = message.get('content')
                            if isinstance(content, str) and 'base64,' in content:
                                print(f"  {role}: [IMAGE]")
                            else:
                                print(f"  {role}: [MESSAGE]")
                        else:
                            print("  [Invalid message format]")
                else:
                    print("  [Invalid message list format]")

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


def process_models_concurrently(context_messages: List[Dict], screenshot_message: List[Dict], aiming_model, gameplay_model):
    """
    Runs aiming and gameplay models concurrently, prioritizing aiming results.
    Returns coordinates if found, otherwise tool_calls from gameplay.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_aiming = run_model_async(executor, aiming_model, screenshot_message)
        messages_with_context = context_messages + screenshot_message
        future_gameplay = run_model_async(executor, gameplay_model, messages_with_context)

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
    screenshot_message, base64_image = get_screenshot_message(desktop, filename=screenshot_path)
    elapsed_time = time.perf_counter() - start_time
    print(f"  [Time] Screenshot: {elapsed_time:.4f}s")
    return screenshot_message, base64_image

def get_action_message(action: str) -> List[Dict]:
    return [{
        "role": "assistant",
        "content": action
    }]

def decide_and_act(coords, tool_calls, gameplay_time, desktop, image_logger, gameplay_model):
    if coords:
        print(f"  [Action] Coords found: {coords}. Aiming & Shooting.")
        perform_aiming_sequence(coords, desktop, image_logger)
        return f"Aim & Shoot. Coords: {coords}"
    
    if tool_calls:
        print(f"  [Action] No Coords. Using Gameplay Model Tool Calls.")
        if gameplay_time > 0:
            print(f"  [Time] Gameplay Model: {gameplay_time:.4f}s")
        handle_gameplay_actions(tool_calls, gameplay_model)
        return f"Tool Calls: {tool_calls[0].function.name}, Arguments: {tool_calls[0].function.arguments}"
    
    print(f"  [Action] No Coords, No Tool Calls.")
    if gameplay_time > 0:
        print(f"  [Time] Gameplay Model (no valid output): {gameplay_time:.4f}s")
    return "No Action"

def run_agent(aiming_model: AimingModel,
              gameplay_model: OpenRouterGameplayModel, 
              desktop: Sandbox, 
              iterations:int =10,
              image_logging_path: str = "images"):
    
    image_logger = ImageLoggingSettings(base_path=image_logging_path)
    agent_memory = AgentMemory(max_iterations=2) 

    for i in range(iterations):
        print(f"\n--- Iteration {i + 1} ---")
        iteration_start = time.perf_counter()

        context_messages = agent_memory.get_memory_as_messages()
        screenshot_message, base64_image = capture_screenshot(desktop, image_logger)

        coords, tool_calls, aiming_time, gameplay_time = process_models_concurrently(
            context_messages,
            screenshot_message,
            aiming_model,
            gameplay_model,
        )
        print(f"  [Time] Aiming Model: {aiming_time:.4f}s")

        action_taken = decide_and_act(
            coords, tool_calls, gameplay_time, desktop, image_logger, gameplay_model
        )

        iteration_end = time.perf_counter()
        print(f" Action taken: {action_taken}")
        print(f"  [Time] Iteration {i+1} Total: {iteration_end - iteration_start:.4f}s")

        action_message = get_action_message(action_taken)
        small_base64_image = compress_and_scale_base64_image(base64_image,
                                                             target_size_percentage=50,
                                                            scale_percentage=20)
        compressed_image_message = get_screenshot_message_from_base64(small_base64_image)

        agent_memory.add_iteration(action_message=action_message, screenshot_message=compressed_image_message)
        agent_memory.print_memory()

    return agent_memory

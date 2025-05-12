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
                 wait_on_start: int = 0,
                 memory: int = 3
                 ):
        """
        :param side: 'CT' or 'T'
        """
        
        self.open_router_key_name = open_router_api_key_name
        self.memory = memory
        if side == "CT":
            self.aiming_system_prompt = CT_AIMING_PROMPT
            self.team_choice = "2"
            self.skin_choice = "2"
        elif side == "T":
            self.aiming_system_prompt = T_AIMING_PROMPT
            self.team_choice = "1"
            self.skin_choice = "4"
        else:
            raise ValueError("Please choose a valid side from ['CT', 'T'].")
        
        
class AgentMemory:
    def __init__(self, max_iterations: int = 3):
        # retain up to `max_iterations` of (actions, screenshots) pairs
        self.iterations = collections.deque(maxlen=max_iterations)

    def add_iteration(
        self,
        action_message: List[Dict],
        screenshot_message: List[Dict]
    ):
        """
        action_message: e.g. [{'role': 'assistant', 'content': 'No Action'}]
        screenshot_message: e.g. [{
            'role': 'user',
            'content': [
                {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,...'}}
            ]
        }]
        """
        self.iterations.append((action_message, screenshot_message))

    def get_action_memory(self) -> List[Dict]:
        """
        Returns a flat list of all action messages in memory,
        in the same shape they were added.
        """
        actions: List[Dict] = []
        for action_msgs, _ in self.iterations:
            actions.extend(action_msgs)
        return actions

    def get_image_memory(self) -> List[Dict]:
        """
        Returns a flat list of image-url dicts only, 
        e.g. [
            {'type': 'image_url', 'image_url': {'url': 'data:image/...'}},
            ...
        ]
        """
        images: List[Dict] = []
        for _, screenshot_msgs in self.iterations:
            for msg in screenshot_msgs:
                # msg['content'] is a list of image dicts
                content = msg.get('content', [])
                if isinstance(content, list):
                    for img in content:
                        # optionally validate img['type'] == 'image_url'
                        images.append(img)
        return images


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


def combine_screenshot_message_with_image_history(
    image_history_messages: List[Dict],
    screenshot_message: List[Dict]
) -> List[Dict]:
    """
    Prepends the list of image-history dicts to each screenshot message's content.

    Args:
        image_history_messages: List of image_url dicts, e.g.
            [
                {'type': 'image_url', 'image_url': {'url': 'data:image/...'}},
                ...
            ]
        screenshot_message: List of messages of the form:
            [
                {
                    'role': 'user',
                    'content': [
                        {'type': 'image_url', 'image_url': {'url': 'data:image/...'}},
                        ...
                    ]
                },
                ...
            ]

    Returns:
        A new list of screenshot messages where each message's "content"
        list has image_history_messages prepended.
    """
    combined_messages: List[Dict] = []

    for msg in screenshot_message:
        new_msg = msg.copy()
        original_content = new_msg.get('content', [])
        if isinstance(original_content, list):
            new_msg['content'] = image_history_messages + original_content
        else:
            new_msg['content'] = image_history_messages + [original_content]
        combined_messages.append(new_msg)

    return combined_messages
    


def process_models_concurrently(action_messages: List[Dict],
                                image_history_messages,
                                screenshot_message: List[Dict],
                                aiming_model,
                                gameplay_model):
    """
    Runs aiming and gameplay models concurrently, prioritizing aiming results.
    Returns coordinates if found, otherwise tool_calls from gameplay.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_aiming = run_model_async(executor, aiming_model, screenshot_message)

        screenshot_message_with_image_history = combine_screenshot_message_with_image_history(image_history_messages,
                                                                                              screenshot_message=screenshot_message)
        messages_with_context = action_messages + screenshot_message_with_image_history
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
        return f"Action taken {tool_calls[0].function.name}, with the sequence: {tool_calls[0].function.arguments}"
    
    print(f"  [Action] No Coords, No Tool Calls.")
    if gameplay_time > 0:
        print(f"  [Time] Gameplay Model (no valid output): {gameplay_time:.4f}s")
    return "No Action"

def run_agent(aiming_model: AimingModel,
              gameplay_model: OpenRouterGameplayModel, 
              desktop: Sandbox, 
              memory_capacity: int = 3,
              iterations:int =10,
              image_logging_path: str = "images"):
    
    image_logger = ImageLoggingSettings(base_path=image_logging_path)
    agent_memory = AgentMemory(max_iterations=memory_capacity) 

    for i in range(iterations):
        print(f"\n--- Iteration {i + 1} ---")
        iteration_start = time.perf_counter()

        action_history = agent_memory.get_action_memory()
        image_history = agent_memory.get_image_memory()
        screenshot_message, base64_image = capture_screenshot(desktop, image_logger)

        coords, tool_calls, aiming_time, gameplay_time = process_models_concurrently(
            action_messages=action_history,
            image_history_messages=image_history,
            screenshot_message=screenshot_message,
            aiming_model=aiming_model,
            gameplay_model=gameplay_model,
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

    return agent_memory

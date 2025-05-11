from abc import ABC, abstractmethod
from e2b_desktop import Sandbox

class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self):
        pass

    @property
    @abstractmethod
    def function_schema(self):
        pass

    @abstractmethod
    def execute(self, **kwargs):
        pass
    

class MoveTool(BaseTool):
    name = "move_tool"
    # function_schema is a dictionary that describes the function and its parameters
    function_schema = {
        "type": "function",
        "function": {
            "name": name,
            "description": "Moves the character using a sequence of 5 basic directions. The actions will be executed in a sequence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key_sequence": {
                        "type": "string",
                        "description": "A string consisting of 5 characters. Each character must be one of 'w' (forward), 'a' (strafe left), 's' (backward), 'd' (strafe right), 'r' (turn right), or 'l' (turn left). Example: 'wwraa' will move forward twice, turn right and strafe left twice."
                    }
                },
                "required": ["key_sequence"]
            }
        }
    }

    def __init__(self, desktop: "Sandbox"):
        self.desktop = desktop

    def execute_turning(self, direction: str):
        if direction == "r":     
            self.desktop.move_mouse(1380, 540) # keep y constant
        if direction == "l":                  # 960 would be the middle for x. We are moving 320 pixels
            self.desktop.move_mouse(540, 540) 
    
    def execute(self, key_sequence: str):
        sequence_to_write = ""
        for action in key_sequence:
            if (action == "r") or (action == "l"):
                if sequence_to_write != "": 
                    self.desktop.write(sequence_to_write) # execute the actions before turning
                    sequence_to_write = ""

                self.execute_turning(action)
            else:
                sequence_to_write += action * 10

        # print(f"moving with key sequence: {key_sequence}")
        # print(sequence_to_write)
        self.desktop.write(sequence_to_write)
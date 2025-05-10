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
            "description": "Moves the character using a sequence of 10 to 20 basic directional key presses. Each character in the sequence represents a single key press.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key_sequence": {
                        "type": "string",
                        "description": "A string consisting of 10 to 20 characters. Each character must be one of 'w' (forward), 'a' (strafe left), 's' (backward), or 'd' (strafe right). Example: 'wwwwwaaaad'"
                    }
                },
                "required": ["key_sequence"]
            }
        }
    }

    def __init__(self, desktop: "Sandbox"):
        self.desktop = desktop
    
    def execute(self, key_sequence: str):
        print(f"moving with key sequence: {key_sequence}")
        self.desktop.write(key_sequence)
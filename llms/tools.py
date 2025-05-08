from abc import ABC, abstractmethod


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
    name = "move_to_location"
    function_schema = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": "Move to the location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city, e.g. San Francisco"
                            },
                        },
                        "required": ["location"]
                    }
                }
            }
    
    def execute(self, location):
        print(f"moving to {location}")
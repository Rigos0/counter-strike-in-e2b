from abc import ABC, abstractmethod
import os
from dotenv import load_dotenv
from typing import Dict, List, Tuple
import json

from openai import OpenAI


load_dotenv()


class BaseFunction(ABC):
    @property
    @abstractmethod
    def function_schema(self):
        pass

    @abstractmethod
    def execute(self, **kwargs):
        pass


class OpenAIModel:
    """
    Communicates with the OpenAI Api

    :param tools: Dict avaliable tools. Example: \
    tools = {
            "execute_python": ExecutePythonFunction(robot),
            "move": MoveFunction(robot),
            "speak": SpeakFunction(robot)
            }
    """
    def __init__(self, 
                 tools: Dict[str, BaseFunction] = {},
                 model: str="gpt-4o"):
        
        self.model = model
        self.default_image_quality = "low"

        load_dotenv()
        openai_api_key = os.environ.get("OPEN_AI_KEY")
        self.client = OpenAI(api_key=openai_api_key)
        self.tools = tools

    def complete(self, messages: list):
        """
        Sends a conversation to the OpenAI API and processes responses,
        including tool calls when required.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=[tool.function_schema for tool in self.tools.values()],
            tool_choice="auto"
        )

        response_message = response.choices[0].message

        print(response_message)

        if response_message.tool_calls:
            tool_responses = self._handle_tool_calls(response_message.tool_calls)        

        return response_message.content, messages, response_message
    

    def _handle_tool_calls(self, tool_calls):
        """
        Handles execution of tool calls requested by the model.

        Args:
            tool_calls (list): List of tool calls requested by the model.

        Returns:
            list: List of responses from the executed tools.
        """
        tool_call_responses = []

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Arguments: {arguments}")

            if tool_name not in self.tools:
                print(f"The model halucinated a tool {tool_name}. The tool is not defined.")
                continue

            tool_response = self.tools[tool_name].execute(**arguments)
            # tool_call_responses.append({
            #     "role": "tool",
            #     "tool_call_id": tool_call.id,
            #     "name": tool_name,
            #     "content": tool_response
            # })

        return tool_call_responses
    

class GroqModel(OpenAIModel):
    def __init__(self, 
                 tools: Dict[str, BaseFunction] = {},
                 model: str = "meta-llama/llama-4-scout-17b-16e-instruct"):

        self.model = model
        self.default_image_quality = "low"

        load_dotenv()
        groq_api_key = os.environ.get("GROQ_API_KEY")
        self.client = OpenAI(base_url="https://api.groq.com/openai/v1",
                             api_key=groq_api_key)
        self.tools = tools


class MemoryManager:
    def __init__(self):
        self.system_prompt = {
            "role": "system",
            "content": " Output only a function call, nothing else."
        }


    def get_memory_as_messages(self):
        """Returns stored memory as a flat list of messages, ensuring system prompt is included."""
        return [self.system_prompt]

    
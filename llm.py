from abc import ABC, abstractmethod
import os
from dotenv import load_dotenv
from typing import Dict, List, Tuple
import json

from openai import OpenAI


load_dotenv()


class BaseFunction(ABC):
    """
    Abstract class for defining a function with schema and execution logic.
    """

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
    """
    def __init__(self):
        self.model = "gpt-4o-mini"
        self.default_image_quality = "low"

        load_dotenv()
        openai_api_key = os.environ.get("OPEN_AI_KEY")
        self.client = OpenAI(api_key=openai_api_key)

        # Examples
        self.available_tools = {
            "execute_python": ExecutePythonFunction(robot),
            "move": MoveFunction(robot),
            "speak": SpeakFunction(robot)
        }

    def complete(self, messages: list):
        """
        Sends a conversation to the OpenAI API and processes responses,
        including tool calls when required.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=[tool.function_schema for tool in self.available_tools.values()],
            tool_choice="auto"
        )

        response_message = response.choices[0].message

        # print("Initial response: ")
        # print(response_message)
        # print("\n")

        # Append the assistant's response to maintain conversation history
        messages.append({
            "role": "assistant",
            "content": response_message.content,
            "tool_calls": response_message.tool_calls
        })

        # Process any tool calls requested by the model
        if response_message.tool_calls:
            tool_responses = self._handle_tool_calls(response_message.tool_calls)

            # Append tool responses to messages
            messages.extend(tool_responses)

            # Re-run the conversation with updated messages
            return self.complete(messages)

        return response_message.content, messages

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

            if tool_name in self.available_tools:
                tool_response = self.available_tools[tool_name].execute(**arguments)

                tool_call_responses.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": tool_response
                })

        return tool_call_responses



    
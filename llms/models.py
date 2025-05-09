import os
from dotenv import load_dotenv
from typing import Dict, List, Tuple, Optional
import json
from abc import ABC, abstractmethod


from openai import OpenAI
from llms.tools import BaseTool

load_dotenv()

class BaseModel(ABC):
    @abstractmethod
    def complete(self, **kwargs):
        pass



class OpenAIModel(BaseModel):
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
                 tools: Dict[str, BaseTool] = {},
                 model: str="gpt-4o"):
        
        self.model = model
        self.default_image_quality = "low"

        openai_api_key = os.environ.get("OPEN_AI_KEY")
        self.client = OpenAI(api_key=openai_api_key)
        self.tools = tools

    def complete(self, messages: List):
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

        if response_message.tool_calls:
            tool_responses = self._handle_tool_calls(response_message.tool_calls)        

        return response_message.content, response

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
                 tools: Dict[str, BaseTool] = {},
                 model: str = "meta-llama/llama-4-scout-17b-16e-instruct"):

        self.model = model

        groq_api_key = os.environ.get("GROQ_API_KEY")
        self.client = OpenAI(base_url="https://api.groq.com/openai/v1",
                             api_key=groq_api_key)
        self.tools = tools


class BaseOpenRouterModel(BaseModel):
    "No tools" 
    def __init__(self, 
                 model: str = "qwen/qwen2.5-vl-3b-instruct:free"):

        self.model = model
        open_router_api_key = os.environ.get("OPENROUTER_API_KEY")
        self.client = OpenAI(base_url="https://openrouter.ai/api/v1",
                             api_key=open_router_api_key)
        

    def complete(self, messages: List):
        # Don't include the system message here.
        # Image should be provided to locate the enemy.

        response = self.client.chat.completions.create(
            model= self.model,
            temperature=self.temperature,
            messages=messages,
        )

        if not response.id:
            print(f"Response blocked: {response}")
            return None, response

        response_message = response.choices[0].message

        return response_message.content, response


class AimingModel(BaseOpenRouterModel):
    # Only the Qwen2.5 VL models support grounding
    # https://openrouter.ai/qwen/
    ALLOWED_MODELS = [
        "qwen/qwen2.5-vl-3b-instruct:free",
        "qwen/qwen-2.5-vl-7b-instruct:free",
        "qwen/qwen-2.5-vl-7b-instruct",
        "qwen/qwen2.5-vl-32b-instruct:free",
        "qwen/qwen2.5-vl-32b-instruct",
        "qwen/qwen2.5-vl-72b-instruct",
    ]

    # Default fallback order
    MODELS_ORDERED = [
        "qwen/qwen2.5-vl-32b-instruct",
        "qwen/qwen2.5-vl-72b-instruct", 
        "qwen/qwen-2.5-vl-7b-instruct",
        "qwen/qwen2.5-vl-32b-instruct:free"]

    example_response = json.dumps(
    {
        "point": {"x": "500", "y": "452"},
    },
    ensure_ascii=False
    )

    system_message = {
            "role": "system",
            "content": f"""Locate the middle point of the head of the nearest standing person from counterstrike gameplay. Output JSON containing the point.
            Important: Don't provide any reasoning, only JSON. If there is no person return "None".
            Example:
            
            Q: <provided gameplay image>
            A: {example_response}"""
        }

    def __init__(self, 
                 model: str = "qwen/qwen2.5-vl-32b-instruct",
                 system_message = system_message,
                 temperature: Optional[float | None] = None):

        if model not in self.ALLOWED_MODELS:
            raise ValueError(f"Model '{model}' can't be used for aiming. Allowed models are: {self.ALLOWED_MODELS}")
        
        print(self.MODELS_ORDERED)
        print(model)
        self.fallback_models = [m for m in self.MODELS_ORDERED if m != model]
        print(self.fallback_models)

        super().__init__(model=model)
        self.system_message = system_message
        self.temperature = temperature


    def complete(self, user_messages: List, debug: bool = False):
        # Don't include the system message as a parameter
        # Image should be provided to locate the enemy.

        messages = [self.system_message] + user_messages
        response = self.client.chat.completions.create(
            model= self.model,
            extra_body={
                        "models": self.fallback_models,
                        "provider": {
                             "ignore": ["Together"] # Together is expensive
                            },
                        },
            temperature=self.temperature,
            messages=messages,
        )

        if debug: 
            print(response)

        if not response.id:
            print(f"Response blocked: {response}")
            return None, response

        response_message = response.choices[0].message

        return response_message.content, response
    
    def parse_point_json(self, model_response: str):
        """
        Parse a single point from a JSON string or dict of the form:
        { "point": { "x": "678", "y": "691" } }

        Args:
            model_response (str or dict): JSON string or already-decoded dict.

        Returns:
            dict: { 'x': int, 'y': int } or None if format is invalid.
        """
        try:
            if isinstance(model_response, str):
                cleaned = model_response.strip().strip("`").strip("json").strip()
                data = json.loads(cleaned)
            else:
                data = model_response

            point = data.get("point", {})
            x = point.get("x")
            y = point.get("y")

            if x is None or y is None:
                raise ValueError("Missing 'x' or 'y' keys in 'point'.")

            return {
                'x': int(x),
                'y': int(y)
            }

        except Exception as e:
            print("Model did not adhere to the aiming structure.")
            print("Error:", str(e))
            print("Model response:", model_response)
            return None
        

class GeminiAimingModel(AimingModel):
    # Gemini models seem to also support grounding.
    # https://ai.google.dev/gemini-api/docs/image-understanding#python_4
    ALLOWED_MODELS = [
        "google/gemini-2.0-flash-exp:free",
        "google/gemini-2.5-flash-preview"
    ]


    def __init__(self, 
                 model: str = "google/gemini-2.0-flash-exp:free"):

        super().__init__(model=model)

    # TODO: Gemini coordinates need to be descaled.
    # see: https://ai.google.dev/gemini-api/docs/image-understanding#bbox
    def complete(self, messages: List):
        # Don't include the system message here.
        # Image should be provided to locate the enemy.

        messages.insert(0, self.system_message)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )

        print(response)

        response_message = response.choices[0].message

        return response_message.content, response


class MemoryManager:
    def __init__(self):
        self.system_prompt = {
            "role": "system",
            "content": " Output only a function call, nothing else."
        }


    def get_memory_as_messages(self):
        """Returns stored memory as a flat list of messages, ensuring system prompt is included."""
        return [self.system_prompt]

    
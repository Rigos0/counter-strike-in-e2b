from abc import ABC, abstractmethod
from typing import Tuple, Any, Dict, List, Callable, Optional, Protocol, TypeVar

from e2b_desktop import Sandbox

_T = TypeVar('_T')

class Step:
    def __init__(self, method_path: str, args: Tuple, kwargs: Dict):
        self.method_path = method_path
        self.args = args
        self.kwargs = kwargs

    def run(self, target: Any):
        current = target
        components = self.method_path.split('.')
        for component in components[:-1]:
            current = getattr(current, component)
        method = getattr(current, components[-1])
        return method(*self.args, **self.kwargs)

    def __repr__(self):
        return f"Step(method={self.method_path}, args={self.args}, kwargs={self.kwargs})"

class CommandsProxy:
    def __init__(self, steps: List[Step], path_prefix: str):
        self._steps = steps
        self._path_prefix = path_prefix

    def run(self, command: str):
        self._steps.append(Step(f"{self._path_prefix}.run", (command,), {}))
        return None # Recording, so no direct return

class SandboxAddProxy:
    def __init__(self, steps: List[Step]):
        self._steps = steps

    def open(self, url: str):
        self._steps.append(Step("open", (url,), {}))
        return None # Recording

    @property
    def commands(self):
        return CommandsProxy(self._steps, "commands")

class DesktopSteps:
    def __init__(self):
        self._steps: List[Step] = []
        self.add = SandboxAddProxy(self._steps)

    def run(self, sandbox: Sandbox):
        for step in self._steps:
            step.run(sandbox)

    def clear(self):
        self._steps.clear()
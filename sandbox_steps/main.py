from abc import ABC, abstractmethod
from typing import Tuple, Any, Dict, List, Callable, Optional, Dict
import inspect


from e2b_desktop import Sandbox


class Step:
    """
    Single step to execute on E2B desktop
    """
    def __init__(self, method_name: str, args: Tuple, kwargs: Dict):
        self.method_name = method_name
        self.args = args
        self.kwargs = kwargs

    def run(self, target: Any):
        method = getattr(target, self.method_name)
        method(*self.args, **self.kwargs)

    def __repr__(self):
        return f"Step(method={self.method_name}, args={self.args}, kwargs={self.kwargs})"
    

class _Recorder(Sandbox):
    def __init__(self, steps: List[Step]):
        object.__setattr__(self, "_steps", steps)

    def __getattribute__(self, name: str) -> Any:
        if name.startswith("_"):
            return object.__getattribute__(self, name)

        attr = getattr(super(), name) 
        if not callable(attr):
            return attr

        def _wrapper(*args, **kwargs):
            self._steps.append(Step(name, args, kwargs))

        # IDE hints trick
        return inspect.signature(attr).bind_partial and _wrapper  # type: ignore


class DesktopSteps:
    def __init__(self):
        self._steps: List[Step] = []
        self.add: Sandbox = _Recorder(self._steps)

    def run(self, sandbox: Sandbox):
        for step in self._steps:
            step.run(sandbox)

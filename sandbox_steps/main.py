from abc import ABC, abstractmethod
from typing import Tuple, Any, Dict, List, Callable, Optional
import inspect

from e2b_desktop import Sandbox


class Step:
    """
    Single step to execute on E2B desktop
    """
    def __init__(self, method_path: str, args: Tuple, kwargs: Dict):
        self.method_path = method_path
        self.args = args
        self.kwargs = kwargs

    def run(self, target: Any):
        # Navigate the path to find the right method
        current = target
        components = self.method_path.split('.')
        
        # Navigate through the nested attributes
        for component in components[:-1]:
            current = getattr(current, component)
        
        # Get the final method and call it
        method = getattr(current, components[-1])
        return method(*self.args, **self.kwargs)

    def __repr__(self):
        return f"Step(method={self.method_path}, args={self.args}, kwargs={self.kwargs})"


class _RecorderProxy:
    """
    A proxy object that records method calls as Steps
    """
    def __init__(self, steps: List[Step], path_prefix: str = ""):
        self._steps = steps
        self._path_prefix = path_prefix
        self._real_sandbox = None
        
    def __getattr__(self, name: str) -> Any:
        # Lazily initialize a real sandbox if needed for introspection
        if self._real_sandbox is None:
            self._real_sandbox = Sandbox()
            
        # Get the actual attribute to check its type
        try:
            real_attr = self._get_real_attr(name)
            
            # If it's a callable, return a function that records the call
            if callable(real_attr):
                return self._make_recorder_method(name)
            # If it's another object, return a new proxy with an updated path
            else:
                new_path = f"{self._path_prefix}.{name}" if self._path_prefix else name
                return _RecorderProxy(self._steps, new_path)
                
        except AttributeError:
            # If attribute doesn't exist, raise an error
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
    
    def _get_real_attr(self, name):
        """Get the real attribute from the sandbox"""
        if not self._path_prefix:
            return getattr(self._real_sandbox, name)
        
        # Navigate through the object path to get the attribute
        obj = self._real_sandbox
        for part in self._path_prefix.split('.'):
            obj = getattr(obj, part)
        return getattr(obj, name)
    
    def _make_recorder_method(self, name):
        """Create a method that records calls"""
        method_path = f"{self._path_prefix}.{name}" if self._path_prefix else name
        
        def recorder_method(*args, **kwargs):
            self._steps.append(Step(method_path, args, kwargs))
            return None  # Return None as we're just recording
            
        return recorder_method


class DesktopSteps:
    def __init__(self):
        self._steps: List[Step] = []
        self.add = _RecorderProxy(self._steps)

    def run(self, sandbox: Sandbox):
        for step in self._steps:
            step.run(sandbox)
            
    def clear(self):
        """Clear all recorded steps"""
        self._steps.clear()
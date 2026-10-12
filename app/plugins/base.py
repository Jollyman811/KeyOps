from typing import Callable, Dict

# Simple registry for action handlers
REGISTRY: Dict[str, Callable] = {}

def register(name: str):
    def deco(fn: Callable):
        REGISTRY[name] = fn
        return fn
    return deco

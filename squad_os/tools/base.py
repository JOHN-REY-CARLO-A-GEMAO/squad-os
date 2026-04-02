import asyncio
import functools
from typing import Any, Dict, Optional


def retry_on_failure(max_attempts: int = 3, delay: float = 1.0):
    """Decorator that retries a tool on exception, then falls back if defined."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return await func(self, *args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay * (attempt + 1))
            # All attempts exhausted — delegate to fallback if set
            fallback = getattr(self, 'fallback_tool', None)
            if fallback:
                if isinstance(fallback, str):
                    # Placeholder; resolved by agent at call site
                    return f"RETRY_EXHAUSTED:{last_error}|FALLBACK:{fallback}"
                try:
                    return await fallback.execute(*args, **kwargs)
                except Exception as fb_e:
                    return f"Retry failed ({last_error}) and fallback also failed ({fb_e})"
            return f"Tool error after {max_attempts} attempts: {last_error}"
        return wrapper
    return decorator


class BaseTool:
    name: str = ""
    description: str = ""
    parameters: Optional[Dict[str, Any]] = None
    fallback_tool: Optional[Any] = None  # Set by subclass or injected by agent

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        if parameters is None:
            default_params = self.__class__.parameters
            self.parameters = dict(default_params) if isinstance(default_params, dict) else {}
        else:
            self.parameters = dict(parameters)

    async def execute(self, **kwargs) -> str:
        raise NotImplementedError("Subclasses must implement execute")

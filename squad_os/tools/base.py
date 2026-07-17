import asyncio
import functools
from typing import Any, Dict, Optional


class RetryExhaustedResult:
    """Result type indicating all retries exhausted with optional fallback."""
    def __init__(self, error: str, fallback_name: Optional[str] = None):
        self.error = error
        self.fallback_name = fallback_name

    def __str__(self) -> str:
        if self.fallback_name:
            return f"RETRY_EXHAUSTED:{self.error}|FALLBACK:{self.fallback_name}"
        return f"RETRY_EXHAUSTED:{self.error}"


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
            fallback_name = getattr(self, 'fallback_name', None)
            fallback = getattr(self, 'fallback_tool', None)
            if fallback:
                if isinstance(fallback, str):
                    # Fallback is a tool name string; return structured result for agent resolution
                    return RetryExhaustedResult(str(last_error), fallback)
                try:
                    return await fallback.execute(*args, **kwargs)
                except Exception as fb_e:
                    return f"Retry failed ({last_error}) and fallback also failed ({fb_e})"
            if fallback_name:
                # Fallback name is defined but not yet resolved to tool instance
                return RetryExhaustedResult(str(last_error), fallback_name)
            return f"Tool error after {max_attempts} attempts: {last_error}"
        return wrapper
    return decorator


class BaseTool:
    name: str = ""
    description: str = ""
    parameters: Optional[Dict[str, Any]] = None
    fallback_name: Optional[str] = None  # Name of fallback tool; resolved by agent through tool_inventory
    fallback_tool: Optional[Any] = None  # Direct tool instance; used if set
    destructive: bool = False  # If True, execution pauses for human approval before first use

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        if parameters is None:
            default_params = self.__class__.parameters
            self.parameters = dict(default_params) if isinstance(default_params, dict) else {}
        else:
            self.parameters = dict(parameters)

    async def execute(self, **kwargs) -> str:
        raise NotImplementedError("Subclasses must implement execute")

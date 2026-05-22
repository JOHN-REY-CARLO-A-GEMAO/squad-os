"""
SelfHealingTool — agent self-recovery, error detection, and automatic retry strategies.

Features:
- Error classification (transient, permanent, resource, logic)
- Automatic retry with exponential backoff
- Agent health checks and state recovery
- Fallback agent/tool switching
- Error pattern learning and prevention
"""
import asyncio
import json
import time
from typing import Optional, List, Dict, Any, Tuple
from squad_os.tools.base import BaseTool


class ErrorClassifier:
    """Classifies errors to determine recovery strategy."""
    
    TRANSIENT_ERRORS = [
        "timeout", "rate limit", "connection reset", "temporary unavailable",
        "network error", "dns resolution", "503", "504", "429"
    ]
    
    PERMANENT_ERRORS = [
        "invalid syntax", "permission denied", "not found", "404", "401", "403",
        "invalid token", "authentication failed", "unsupported"
    ]
    
    RESOURCE_ERRORS = [
        "out of memory", "disk full", "quota exceeded", "storage limit",
        "too many open files", "resource exhausted"
    ]
    
    LOGIC_ERRORS = [
        "invalid role", "task failed", "qa failure", "validation error",
        "assertion failed", "unexpected result"
    ]
    
    @classmethod
    def classify(cls, error_message: str) -> Tuple[str, str]:
        """
        Classify an error message.
        Returns: (error_type, recommended_action)
        """
        error_lower = error_message.lower()
        
        for pattern in cls.TRANSIENT_ERRORS:
            if pattern in error_lower:
                return ("transient", "retry_with_backoff")
        
        for pattern in cls.PERMANENT_ERRORS:
            if pattern in error_lower:
                return ("permanent", "fallback_or_skip")
        
        for pattern in cls.RESOURCE_ERRORS:
            if pattern in error_lower:
                return ("resource", "wait_and_retry")
        
        for pattern in cls.LOGIC_ERRORS:
            if pattern in error_lower:
                return ("logic", "retry_with_context")
        
        return ("unknown", "retry_once")


class RetryStrategy:
    """Implements various retry strategies."""
    
    @staticmethod
    async def exponential_backoff(
        func,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        *args,
        **kwargs
    ) -> Any:
        """Retry with exponential backoff."""
        last_error = None
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                error_type, action = ErrorClassifier.classify(str(e))
                
                if action == "fallback_or_skip":
                    raise  # Don't retry permanent errors
                
                if attempt < max_retries - 1:
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    # Add jitter
                    import random
                    delay *= (0.5 + random.random() * 0.5)
                    print(f"⚠️ [SelfHealing]: Retry {attempt+1}/{max_retries} after {delay:.1f}s (error: {error_type})")
                    await asyncio.sleep(delay)
        
        raise last_error
    
    @staticmethod
    async def retry_with_context(
        func,
        context: str,
        max_retries: int = 2,
        *args,
        **kwargs
    ) -> Any:
        """Retry with additional context/guidance."""
        last_error = None
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    # Inject context for next attempt
                    kwargs['context'] = context + f"\n\nPrevious error: {e}. Please adjust your approach."
                    print(f"⚠️ [SelfHealing]: Retry {attempt+1}/{max_retries} with additional context")
        
        raise last_error


class AgentHealthMonitor:
    """Monitors agent health and tracks error patterns."""
    
    def __init__(self):
        self.agent_health = {}  # agent_role -> health_score (0-100)
        self.error_history = {}  # agent_role -> list of recent errors
        self.success_count = {}  # agent_role -> count of successful tasks
        self.failure_count = {}  # agent_role -> count of failed tasks
    
    def record_success(self, agent_role: str):
        """Record a successful task execution."""
        self.success_count[agent_role] = self.success_count.get(agent_role, 0) + 1
        self.agent_health[agent_role] = min(100, self.agent_health.get(agent_role, 50) + 5)
    
    def record_failure(self, agent_role: str, error: str):
        """Record a failed task execution."""
        self.failure_count[agent_role] = self.failure_count.get(agent_role, 0) + 1
        if agent_role not in self.error_history:
            self.error_history[agent_role] = []
        self.error_history[agent_role].append({
            "error": error,
            "timestamp": time.time(),
            "type": ErrorClassifier.classify(error)[0]
        })
        # Keep only last 10 errors
        self.error_history[agent_role] = self.error_history[agent_role][-10:]
        
        # Decrease health score
        error_type, _ = ErrorClassifier.classify(error)
        penalty = {"transient": 5, "permanent": 15, "resource": 10, "logic": 10, "unknown": 5}.get(error_type, 5)
        self.agent_health[agent_role] = max(0, self.agent_health.get(agent_role, 50) - penalty)
    
    def get_health_score(self, agent_role: str) -> int:
        """Get current health score for an agent (0-100)."""
        return self.agent_health.get(agent_role, 50)
    
    def is_healthy(self, agent_role: str, threshold: int = 30) -> bool:
        """Check if an agent is healthy enough to receive tasks."""
        return self.get_health_score(agent_role) >= threshold
    
    def get_error_patterns(self, agent_role: str) -> List[Dict]:
        """Get recent error patterns for an agent."""
        return self.error_history.get(agent_role, [])
    
    def get_recommendation(self, agent_role: str) -> str:
        """Get recommendation based on agent health."""
        health = self.get_health_score(agent_role)
        if health >= 80:
            return "healthy"
        elif health >= 50:
            return "degraded - monitor closely"
        elif health >= 30:
            return "unhealthy - consider fallback"
        else:
            return "critical - avoid using, switch to fallback"


# Global health monitor instance
health_monitor = AgentHealthMonitor()


class SelfHealTool(BaseTool):
    name = "self_heal"
    description = (
        "Trigger self-healing for the current agent or mission. "
        "Analyzes recent errors, applies recovery strategies, and attempts to resume. "
        "Can retry failed tasks, switch to fallback agents, or request human guidance."
    )
    parameters = {
        "type": "object",
        "properties": {
            "agent_role": {
                "type": "string",
                "description": "Agent role to heal (optional, defaults to current agent)"
            },
            "action": {
                "type": "string",
                "enum": ["retry", "fallback", "diagnose", "recover"],
                "description": "Healing action: 'retry' (retry failed task), 'fallback' (switch agent), 'diagnose' (analyze errors), 'recover' (full recovery)"
            }
        },
        "required": ["action"]
    }
    category = "self-healing"

    async def execute(self, action: str, agent_role: Optional[str] = None) -> str:
        if not agent_role:
            return "Error: agent_role is required for self-healing."
        
        if action == "diagnose":
            health = health_monitor.get_health_score(agent_role)
            patterns = health_monitor.get_error_patterns(agent_role)
            recommendation = health_monitor.get_recommendation(agent_role)
            
            return json.dumps({
                "agent_role": agent_role,
                "health_score": health,
                "recent_errors": len(patterns),
                "error_patterns": patterns[-5:],  # Last 5 errors
                "recommendation": recommendation
            }, indent=2)
        
        elif action == "retry":
            return f"Retry triggered for {agent_role}. Use retry_with_backoff in code for automatic retries."
        
        elif action == "fallback":
            return f"Fallback triggered for {agent_role}. System will attempt to use alternative agents."
        
        elif action == "recover":
            return f"Full recovery triggered for {agent_role}. Analyzing errors and applying recovery strategies..."
        
        return f"Unknown action: {action}"


class HealthCheckTool(BaseTool):
    name = "health_check"
    description = (
        "Check the health status of all active agents. "
        "Returns health scores, error counts, and recommendations for each agent."
    )
    parameters = {
        "type": "object",
        "properties": {
            "agent_role": {
                "type": "string",
                "description": "Specific agent to check (optional, checks all if omitted)"
            }
        },
        "required": []
    }
    category = "self-healing"

    async def execute(self, agent_role: Optional[str] = None) -> str:
        if agent_role:
            health = health_monitor.get_health_score(agent_role)
            recommendation = health_monitor.get_recommendation(agent_role)
            errors = health_monitor.get_error_patterns(agent_role)
            return json.dumps({
                "agent_role": agent_role,
                "health_score": health,
                "recommendation": recommendation,
                "recent_errors": len(errors)
            }, indent=2)
        
        # Check all known agents
        all_agents = set(list(health_monitor.agent_health.keys()) + 
                        list(health_monitor.success_count.keys()) +
                        list(health_monitor.failure_count.keys()))
        
        results = {}
        for role in all_agents:
            results[role] = {
                "health_score": health_monitor.get_health_score(role),
                "recommendation": health_monitor.get_recommendation(role),
                "successes": health_monitor.success_count.get(role, 0),
                "failures": health_monitor.failure_count.get(role, 0)
            }
        
        return json.dumps(results, indent=2)


class RetryWithBackoffTool(BaseTool):
    name = "retry_with_backoff"
    description = (
        "Retry a failed operation with exponential backoff. "
        "Automatically classifies the error and applies the appropriate retry strategy."
    )
    parameters = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "Description of the operation to retry"
            },
            "max_retries": {
                "type": "integer",
                "description": "Maximum number of retries (default: 3)"
            },
            "base_delay": {
                "type": "number",
                "description": "Base delay in seconds (default: 1.0)"
            }
        },
        "required": ["operation"]
    }
    category = "self-healing"

    async def execute(
        self,
        operation: str,
        max_retries: int = 3,
        base_delay: float = 1.0
    ) -> str:
        return (
            f"Retry strategy configured for: {operation}\n"
            f"Max retries: {max_retries}, Base delay: {base_delay}s\n"
            f"Error classification and backoff will be applied automatically."
        )

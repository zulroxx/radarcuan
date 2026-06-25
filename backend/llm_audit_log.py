"""LLM audit log untuk tracking semua panggilan LLM."""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class LLMCall:
    """Represents an LLM API call."""
    agent_name: str
    model: str
    prompt_length: int
    response_length: int
    execution_time: float
    success: bool
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class LLMAuditLog:
    """Track all LLM API calls for auditing and monitoring."""
    
    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        self._calls: List[LLMCall] = []
        self._lock = asyncio.Lock()
    
    async def record_call(
        self,
        agent_name: str,
        model: str,
        prompt_length: int,
        response_length: int,
        execution_time: float,
        success: bool,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an LLM API call."""
        async with self._lock:
            call = LLMCall(
                agent_name=agent_name,
                model=model,
                prompt_length=prompt_length,
                response_length=response_length,
                execution_time=execution_time,
                success=success,
                error=error,
                metadata=metadata or {},
            )
            
            self._calls.append(call)
            
            # Keep only last max_entries
            if len(self._calls) > self.max_entries:
                self._calls = self._calls[-self.max_entries:]
    
    async def get_recent_calls(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent LLM calls."""
        async with self._lock:
            recent = self._calls[-limit:]
            return [
                {
                    'agent_name': c.agent_name,
                    'model': c.model,
                    'prompt_length': c.prompt_length,
                    'response_length': c.response_length,
                    'execution_time': c.execution_time,
                    'success': c.success,
                    'timestamp': c.timestamp,
                    'error': c.error,
                    'metadata': c.metadata,
                }
                for c in reversed(recent)
            ]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get LLM call statistics."""
        async with self._lock:
            if not self._calls:
                return {
                    'total_calls': 0,
                    'success_rate': 0.0,
                    'avg_execution_time': 0.0,
                    'avg_prompt_length': 0.0,
                    'avg_response_length': 0.0,
                    'by_agent': {},
                    'by_model': {},
                }
            
            total = len(self._calls)
            successes = sum(1 for c in self._calls if c.success)
            success_rate = (successes / total * 100) if total > 0 else 0.0
            
            execution_times = [c.execution_time for c in self._calls]
            avg_execution_time = sum(execution_times) / len(execution_times)
            
            prompt_lengths = [c.prompt_length for c in self._calls]
            avg_prompt_length = sum(prompt_lengths) / len(prompt_lengths)
            
            response_lengths = [c.response_length for c in self._calls]
            avg_response_length = sum(response_lengths) / len(response_lengths)
            
            # Group by agent
            by_agent = {}
            for call in self._calls:
                if call.agent_name not in by_agent:
                    by_agent[call.agent_name] = {
                        'total_calls': 0,
                        'successes': 0,
                        'total_execution_time': 0.0,
                    }
                by_agent[call.agent_name]['total_calls'] += 1
                if call.success:
                    by_agent[call.agent_name]['successes'] += 1
                by_agent[call.agent_name]['total_execution_time'] += call.execution_time
            
            # Calculate averages for by_agent
            for agent_name, stats in by_agent.items():
                stats['success_rate'] = (stats['successes'] / stats['total_calls'] * 100) if stats['total_calls'] > 0 else 0.0
                stats['avg_execution_time'] = stats['total_execution_time'] / stats['total_calls'] if stats['total_calls'] > 0 else 0.0
            
            # Group by model
            by_model = {}
            for call in self._calls:
                if call.model not in by_model:
                    by_model[call.model] = {
                        'total_calls': 0,
                        'successes': 0,
                    }
                by_model[call.model]['total_calls'] += 1
                if call.success:
                    by_model[call.model]['successes'] += 1
            
            # Calculate success rate for by_model
            for model_name, stats in by_model.items():
                stats['success_rate'] = (stats['successes'] / stats['total_calls'] * 100) if stats['total_calls'] > 0 else 0.0
            
            return {
                'total_calls': total,
                'success_rate': round(success_rate, 2),
                'avg_execution_time': round(avg_execution_time, 3),
                'avg_prompt_length': round(avg_prompt_length, 2),
                'avg_response_length': round(avg_response_length, 2),
                'by_agent': by_agent,
                'by_model': by_model,
            }
    
    async def get_calls_by_agent(self, agent_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get LLM calls for a specific agent."""
        async with self._lock:
            agent_calls = [c for c in self._calls if c.agent_name == agent_name]
            recent = agent_calls[-limit:]
            return [
                {
                    'model': c.model,
                    'prompt_length': c.prompt_length,
                    'response_length': c.response_length,
                    'execution_time': c.execution_time,
                    'success': c.success,
                    'timestamp': c.timestamp,
                    'error': c.error,
                }
                for c in reversed(recent)
            ]
    
    async def clear_logs(self, agent_name: Optional[str] = None) -> None:
        """Clear logs for a specific agent or all agents."""
        async with self._lock:
            if agent_name:
                self._calls = [c for c in self._calls if c.agent_name != agent_name]
            else:
                self._calls.clear()


# Global instance
llm_audit_log = LLMAuditLog(max_entries=10000)

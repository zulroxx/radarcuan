"""Agent metrics tracking untuk monitoring execution time dan success rate."""
import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class AgentMetrics:
    """Track execution metrics for each AI agent."""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self._metrics: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def record_execution(
        self,
        agent_name: str,
        success: bool,
        execution_time: float,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an agent execution."""
        async with self._lock:
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "success": success,
                "execution_time": execution_time,
                "error": error,
                "metadata": metadata or {},
            }
            
            self._metrics[agent_name].append(entry)
            
            # Keep only last window_size entries
            if len(self._metrics[agent_name]) > self.window_size:
                self._metrics[agent_name] = self._metrics[agent_name][-self.window_size:]
    
    async def get_agent_stats(self, agent_name: str) -> Dict[str, Any]:
        """Get statistics for a specific agent."""
        async with self._lock:
            entries = self._metrics.get(agent_name, [])
            
            if not entries:
                return {
                    "agent": agent_name,
                    "total_executions": 0,
                    "success_rate": 0.0,
                    "avg_execution_time": 0.0,
                    "min_execution_time": 0.0,
                    "max_execution_time": 0.0,
                    "last_execution": None,
                    "last_success": None,
                    "recent_errors": [],
                }
            
            total = len(entries)
            successes = sum(1 for e in entries if e["success"])
            success_rate = (successes / total * 100) if total > 0 else 0.0
            
            execution_times = [e["execution_time"] for e in entries]
            avg_time = sum(execution_times) / len(execution_times)
            min_time = min(execution_times)
            max_time = max(execution_times)
            
            last_entry = entries[-1]
            recent_errors = [
                e for e in entries[-10:] if not e["success"] and e.get("error")
            ]
            
            return {
                "agent": agent_name,
                "total_executions": total,
                "success_rate": round(success_rate, 2),
                "avg_execution_time": round(avg_time, 3),
                "min_execution_time": round(min_time, 3),
                "max_execution_time": round(max_time, 3),
                "last_execution": last_entry["timestamp"],
                "last_success": last_entry["success"],
                "recent_errors": recent_errors[-5:],  # Last 5 errors
            }
    
    async def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all agents."""
        async with self._lock:
            agent_names = list(self._metrics.keys())
        
        stats = {}
        for agent_name in agent_names:
            stats[agent_name] = await self.get_agent_stats(agent_name)
        
        return stats
    
    async def get_failure_rate(self, agent_name: str, last_n: int = 10) -> float:
        """Get failure rate for last N executions."""
        async with self._lock:
            entries = self._metrics.get(agent_name, [])
            if len(entries) < last_n:
                return 0.0
            
            recent = entries[-last_n:]
            failures = sum(1 for e in recent if not e["success"])
            return (failures / last_n) * 100
    
    async def clear_metrics(self, agent_name: Optional[str] = None) -> None:
        """Clear metrics for a specific agent or all agents."""
        async with self._lock:
            if agent_name:
                self._metrics[agent_name] = []
            else:
                self._metrics.clear()


class ExecutionTimer:
    """Context manager for timing agent executions."""
    
    def __init__(self, metrics: AgentMetrics, agent_name: str, metadata: Optional[Dict[str, Any]] = None):
        self.metrics = metrics
        self.agent_name = agent_name
        self.metadata = metadata
        self.start_time = None
        self.success = False
        self.error = None
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        execution_time = time.time() - self.start_time
        
        if exc_type is not None:
            self.success = False
            self.error = str(exc_val) if exc_val else str(exc_type)
        else:
            self.success = True
        
        await self.metrics.record_execution(
            agent_name=self.agent_name,
            success=self.success,
            execution_time=execution_time,
            error=self.error,
            metadata=self.metadata,
        )
        
        return False  # Don't suppress exceptions


# Global instance
agent_metrics = AgentMetrics(window_size=100)

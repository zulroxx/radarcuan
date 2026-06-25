"""Circuit breaker pattern untuk mencegah cascading failures antar AI Agent."""
import asyncio
import logging
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker untuk membatasi retry pada agent yang gagal berulang kali.
    
    State machine:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail fast
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 300.0,  # 5 menit
        half_open_max_calls: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.failures = 0
        self.successes = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.half_open_calls = 0
        self._lock = asyncio.Lock()
    
    async def can_execute(self) -> bool:
        """Check jika request boleh dieksekusi."""
        async with self._lock:
            if self.state == "CLOSED":
                return True
            
            if self.state == "OPEN":
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    self.state = "HALF_OPEN"
                    self.half_open_calls = 0
                    logger.info(f"Circuit breaker HALF_OPEN: {self.name}")
                    return True
                return False
            
            if self.state == "HALF_OPEN":
                if self.half_open_calls < self.half_open_max_calls:
                    self.half_open_calls += 1
                    return True
                return False
        
        return False
    
    async def record_success(self) -> None:
        """Record successful execution."""
        async with self._lock:
            if self.state == "HALF_OPEN":
                self.successes += 1
                if self.successes >= 2:
                    self.state = "CLOSED"
                    self.failures = 0
                    self.successes = 0
                    logger.info(f"Circuit breaker CLOSED: {self.name}")
            elif self.state == "CLOSED":
                self.failures = 0
    
    async def record_failure(self) -> None:
        """Record failed execution."""
        async with self._lock:
            self.failures += 1
            self.last_failure_time = time.time()
            
            if self.state == "HALF_OPEN":
                self.state = "OPEN"
                logger.warning(f"Circuit breaker OPEN: {self.name} (failures={self.failures})")
            elif self.state == "CLOSED":
                if self.failures >= self.failure_threshold:
                    self.state = "OPEN"
                    logger.warning(
                        f"Circuit breaker OPEN: {self.name} "
                        f"(threshold={self.failure_threshold}, failures={self.failures})"
                    )
    
    @property
    def name(self) -> str:
        return getattr(self, '_name', 'unknown')
    
    @name.setter
    def name(self, value: str) -> None:
        self._name = value


class CircuitBreakerRegistry:
    """Registry untuk manage circuit breaker per agent."""
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
    
    async def get_breaker(self, agent_name: str) -> CircuitBreaker:
        """Get atau create circuit breaker untuk agent."""
        async with self._lock:
            if agent_name not in self._breakers:
                breaker = CircuitBreaker()
                breaker.name = agent_name
                self._breakers[agent_name] = breaker
            return self._breakers[agent_name]
    
    async def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status semua circuit breaker."""
        async with self._lock:
            return {
                name: {
                    "state": b.state,
                    "failures": b.failures,
                    "successes": b.successes,
                    "last_failure_time": b.last_failure_time,
                }
                for name, b in self._breakers.items()
            }


# Global instance
circuit_breaker_registry = CircuitBreakerRegistry()

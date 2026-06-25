"""Alerting system untuk mendeteksi kegagalan agent dan mengirim notifikasi."""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """Represents an alert event."""
    agent_name: str
    alert_type: str  # 'failure_rate', 'circuit_breaker', 'slow_execution', 'dependency_failure'
    severity: str  # 'warning', 'critical'
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class AlertManager:
    """Manage alerts and trigger notifications."""
    
    def __init__(self):
        self._alerts: List[Alert] = []
        self._alert_handlers: List[Callable[[Alert], None]] = []
        self._lock = asyncio.Lock()
        self._max_alerts = 1000
        
        # Thresholds
        self.failure_rate_threshold = 50.0  # Alert if failure rate > 50%
        self.slow_execution_threshold = 30.0  # Alert if execution time > 30s
        self.min_executions_for_alert = 5  # Minimum executions before alerting
    
    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add a handler function to be called when an alert is triggered."""
        self._alert_handlers.append(handler)
    
    async def trigger_alert(self, alert: Alert) -> None:
        """Trigger an alert and notify all handlers."""
        async with self._lock:
            self._alerts.append(alert)
            
            # Keep only last max_alerts
            if len(self._alerts) > self._max_alerts:
                self._alerts = self._alerts[-self._max_alerts:]
        
        # Log the alert
        log_func = logger.warning if alert.severity == 'warning' else logger.error
        log_func(f"[ALERT] {alert.agent_name}: {alert.message}")
        
        # Notify all handlers
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
    
    async def check_agent_health(
        self,
        agent_name: str,
        success_rate: float,
        avg_execution_time: float,
        total_executions: int,
        circuit_breaker_state: Optional[str] = None,
    ) -> None:
        """Check agent health and trigger alerts if needed."""
        # Check failure rate
        if total_executions >= self.min_executions_for_alert:
            failure_rate = 100.0 - success_rate
            if failure_rate > self.failure_rate_threshold:
                await self.trigger_alert(Alert(
                    agent_name=agent_name,
                    alert_type='failure_rate',
                    severity='critical' if failure_rate > 75.0 else 'warning',
                    message=f"Failure rate {failure_rate:.1f}% exceeds threshold {self.failure_rate_threshold}%",
                    metadata={
                        'failure_rate': failure_rate,
                        'success_rate': success_rate,
                        'total_executions': total_executions,
                    }
                ))
        
        # Check slow execution
        if avg_execution_time > self.slow_execution_threshold:
            await self.trigger_alert(Alert(
                agent_name=agent_name,
                alert_type='slow_execution',
                severity='warning',
                message=f"Average execution time {avg_execution_time:.2f}s exceeds threshold {self.slow_execution_threshold}s",
                metadata={
                    'avg_execution_time': avg_execution_time,
                    'threshold': self.slow_execution_threshold,
                }
            ))
        
        # Check circuit breaker state
        if circuit_breaker_state == 'OPEN':
            await self.trigger_alert(Alert(
                agent_name=agent_name,
                alert_type='circuit_breaker',
                severity='critical',
                message=f"Circuit breaker is OPEN - agent is disabled",
                metadata={
                    'circuit_breaker_state': circuit_breaker_state,
                }
            ))
    
    async def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        async with self._lock:
            recent = self._alerts[-limit:]
            return [
                {
                    'agent_name': a.agent_name,
                    'alert_type': a.alert_type,
                    'severity': a.severity,
                    'message': a.message,
                    'timestamp': a.timestamp,
                    'metadata': a.metadata,
                }
                for a in reversed(recent)
            ]
    
    async def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of alerts."""
        async with self._lock:
            total = len(self._alerts)
            critical = sum(1 for a in self._alerts if a.severity == 'critical')
            warning = sum(1 for a in self._alerts if a.severity == 'warning')
            
            # Count by agent
            by_agent = {}
            for alert in self._alerts:
                if alert.agent_name not in by_agent:
                    by_agent[alert.agent_name] = {'critical': 0, 'warning': 0}
                by_agent[alert.agent_name][alert.severity] += 1
            
            return {
                'total_alerts': total,
                'critical_count': critical,
                'warning_count': warning,
                'by_agent': by_agent,
            }
    
    async def clear_alerts(self, agent_name: Optional[str] = None) -> None:
        """Clear alerts for a specific agent or all agents."""
        async with self._lock:
            if agent_name:
                self._alerts = [a for a in self._alerts if a.agent_name != agent_name]
            else:
                self._alerts.clear()


# Global instance
alert_manager = AlertManager()

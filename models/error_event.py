"""
Error Event data model for system error tracking
"""
import traceback
from datetime import datetime
from typing import Optional, Dict, Any


class ErrorEvent:
    """Represents a system error event for tracking and debugging"""

    # Severity levels
    SEVERITY_LOW = 'LOW'
    SEVERITY_MEDIUM = 'MEDIUM'
    SEVERITY_HIGH = 'HIGH'
    SEVERITY_CRITICAL = 'CRITICAL'
    VALID_SEVERITIES = [SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL]

    # Common component names
    COMPONENT_JOB_MANAGER = 'job_manager'
    COMPONENT_BACKGROUND_MONITOR = 'background_monitor'
    COMPONENT_WEBSOCKET = 'websocket'
    COMPONENT_STORAGE = 'storage'
    COMPONENT_ENGINE = 'engine'
    COMPONENT_UI = 'ui'
    COMPONENT_API = 'api'

    def __init__(
        self,
        severity: str,
        component: str,
        error_type: str,
        message: str,
        details: Optional[str] = None,
        job_id: Optional[str] = None,
        job_name: Optional[str] = None,
        stack_trace: Optional[str] = None,
        event_id: Optional[int] = None,
        timestamp: Optional[datetime] = None,
        resolved: bool = False,
        resolved_at: Optional[datetime] = None
    ):
        """
        Initialize an ErrorEvent

        Args:
            severity: Error severity (LOW, MEDIUM, HIGH, CRITICAL)
            component: Component where error occurred
            error_type: Type of error (e.g., 'FileNotFoundError', 'ConnectionError')
            message: Human-readable error message
            details: Additional details about the error
            job_id: Associated job ID (if applicable)
            job_name: Associated job name (if applicable)
            stack_trace: Full stack trace if available
            event_id: Database ID (None for new events)
            timestamp: When error occurred (auto-set if None)
            resolved: Whether error has been resolved
            resolved_at: When error was resolved
        """
        self.id = event_id
        self.severity = severity
        self.component = component
        self.error_type = error_type
        self.message = message
        self.details = details
        self.job_id = job_id
        self.job_name = job_name
        self.stack_trace = stack_trace
        self.timestamp = timestamp or datetime.now()
        self.resolved = resolved
        self.resolved_at = resolved_at

        # Validate
        if self.severity not in self.VALID_SEVERITIES:
            raise ValueError(f"Invalid severity '{severity}'. Must be one of: {', '.join(self.VALID_SEVERITIES)}")

    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        severity: str,
        component: str,
        message: str,
        job_id: Optional[str] = None,
        job_name: Optional[str] = None
    ) -> 'ErrorEvent':
        """
        Create ErrorEvent from an exception

        Args:
            exception: The exception that occurred
            severity: Error severity level
            component: Component where error occurred
            message: Human-readable context message
            job_id: Associated job ID (if applicable)
            job_name: Associated job name (if applicable)

        Returns:
            ErrorEvent instance
        """
        return cls(
            severity=severity,
            component=component,
            error_type=type(exception).__name__,
            message=message,
            details=str(exception),
            job_id=job_id,
            job_name=job_name,
            stack_trace=''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert ErrorEvent to dictionary

        Returns:
            Dictionary representation
        """
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            'severity': self.severity,
            'component': self.component,
            'error_type': self.error_type,
            'message': self.message,
            'details': self.details,
            'job_id': self.job_id,
            'job_name': self.job_name,
            'stack_trace': self.stack_trace,
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ErrorEvent':
        """
        Create ErrorEvent from dictionary

        Args:
            data: Dictionary with error event data

        Returns:
            ErrorEvent instance
        """
        timestamp = data.get('timestamp')
        if timestamp and isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        resolved_at = data.get('resolved_at')
        if resolved_at and isinstance(resolved_at, str):
            resolved_at = datetime.fromisoformat(resolved_at)

        return ErrorEvent(
            event_id=data.get('id'),
            timestamp=timestamp,
            severity=data['severity'],
            component=data['component'],
            error_type=data['error_type'],
            message=data['message'],
            details=data.get('details'),
            job_id=data.get('job_id'),
            job_name=data.get('job_name'),
            stack_trace=data.get('stack_trace'),
            resolved=data.get('resolved', False),
            resolved_at=resolved_at
        )

    def mark_resolved(self):
        """Mark this error event as resolved"""
        self.resolved = True
        self.resolved_at = datetime.now()

    def __repr__(self) -> str:
        return f"ErrorEvent(id={self.id}, severity={self.severity}, component={self.component}, type={self.error_type})"

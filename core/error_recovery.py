"""
Error Recovery Strategies (Task 6.3)
Implements automatic recovery mechanisms for common failure scenarios
"""
import logging
import time
import functools
from typing import Callable, Any, Optional, Tuple
from core.error_repository import get_error_repository
from models.error_event import ErrorEvent

logger = logging.getLogger(__name__)


class RecoveryStrategy:
    """Base class for error recovery strategies"""

    def __init__(self, max_retries: int = 3, initial_delay: float = 1.0):
        """
        Initialize recovery strategy

        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay between retries (seconds)
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Determine if operation should be retried

        Args:
            exception: The exception that occurred
            attempt: Current attempt number (1-indexed)

        Returns:
            True if should retry, False otherwise
        """
        # Don't retry if max attempts reached
        if attempt > self.max_retries:
            return False

        # Retry transient errors
        transient_errors = (
            IOError,
            OSError,
            TimeoutError,
            ConnectionError,
        )

        return isinstance(exception, transient_errors)

    def get_retry_delay(self, attempt: int) -> float:
        """
        Calculate delay before next retry using exponential backoff

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff: 1s, 2s, 4s, 8s, ...
        return self.initial_delay * (2 ** (attempt - 1))


class ExponentialBackoffRetry:
    """Decorator for automatic retry with exponential backoff"""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        component: str = "unknown",
        log_errors: bool = True
    ):
        """
        Initialize retry decorator

        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay between retries (seconds)
            component: Component name for error logging
            log_errors: Whether to log errors to database
        """
        self.strategy = RecoveryStrategy(max_retries, initial_delay)
        self.component = component
        self.log_errors = log_errors

    def __call__(self, func: Callable) -> Callable:
        """
        Decorate function with retry logic

        Args:
            func: Function to decorate

        Returns:
            Decorated function
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(1, self.strategy.max_retries + 2):
                try:
                    # Try to execute the function
                    return func(*args, **kwargs)

                except Exception as e:
                    last_exception = e

                    # Check if we should retry
                    if attempt <= self.strategy.max_retries and self.strategy.should_retry(e, attempt):
                        delay = self.strategy.get_retry_delay(attempt)
                        logger.warning(
                            f"{self.component}: {func.__name__} failed (attempt {attempt}/{self.strategy.max_retries}). "
                            f"Retrying in {delay}s. Error: {str(e)}"
                        )
                        time.sleep(delay)
                        continue

                    # Max retries reached or non-retriable error
                    logger.error(
                        f"{self.component}: {func.__name__} failed after {attempt} attempts. "
                        f"Error: {str(e)}"
                    )

                    # Log to error database
                    if self.log_errors:
                        try:
                            error_repo = get_error_repository()
                            error_event = ErrorEvent.from_exception(
                                exception=e,
                                severity=ErrorEvent.SEVERITY_MEDIUM,
                                component=self.component,
                                message=f"{func.__name__} failed after {attempt} retry attempts"
                            )
                            error_repo.log_error(error_event)
                        except Exception as log_err:
                            logger.error(f"Failed to log error event: {log_err}")

                    # Re-raise the last exception
                    raise

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    component: str = "unknown",
    log_errors: bool = True
):
    """
    Decorator function for retry with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries (seconds)
        component: Component name for error logging
        log_errors: Whether to log errors to database

    Returns:
        Decorator function

    Example:
        @retry_with_backoff(max_retries=3, component="storage")
        def save_to_storage(data):
            # This function will automatically retry on transient failures
            storage.write(data)
    """
    return ExponentialBackoffRetry(
        max_retries=max_retries,
        initial_delay=initial_delay,
        component=component,
        log_errors=log_errors
    )


class CircuitBreaker:
    """
    Circuit breaker pattern for preventing cascading failures

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, reject requests immediately
    - HALF_OPEN: Testing if system has recovered
    """

    STATE_CLOSED = "closed"
    STATE_OPEN = "open"
    STATE_HALF_OPEN = "half_open"

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        component: str = "unknown"
    ):
        """
        Initialize circuit breaker

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            component: Component name for logging
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.component = component

        self.state = self.STATE_CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0

    def call(self, func: Callable, *args, **kwargs) -> Tuple[bool, Any]:
        """
        Execute function through circuit breaker

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Tuple of (success, result)
        """
        # Check circuit state
        if self.state == self.STATE_OPEN:
            # Check if recovery timeout has passed
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                logger.info(f"{self.component}: Circuit breaker entering HALF_OPEN state")
                self.state = self.STATE_HALF_OPEN
            else:
                # Circuit still open, reject immediately
                logger.warning(f"{self.component}: Circuit breaker OPEN, rejecting request")
                return False, None

        # Try to execute function
        try:
            result = func(*args, **kwargs)

            # Success - reset circuit
            if self.state == self.STATE_HALF_OPEN:
                logger.info(f"{self.component}: Circuit breaker entering CLOSED state (recovered)")
                self.state = self.STATE_CLOSED
                self.failure_count = 0

            return True, result

        except Exception as e:
            # Failure - increment counter
            self.failure_count += 1
            self.last_failure_time = time.time()

            logger.error(f"{self.component}: Circuit breaker failure #{self.failure_count}: {str(e)}")

            # Check if threshold reached
            if self.failure_count >= self.failure_threshold:
                logger.error(
                    f"{self.component}: Circuit breaker OPENED after {self.failure_count} failures. "
                    f"Will retry in {self.recovery_timeout}s"
                )
                self.state = self.STATE_OPEN

                # Log to error database
                try:
                    error_repo = get_error_repository()
                    error_event = ErrorEvent.from_exception(
                        exception=e,
                        severity=ErrorEvent.SEVERITY_HIGH,
                        component=self.component,
                        message=f"Circuit breaker opened after {self.failure_count} failures"
                    )
                    error_repo.log_error(error_event)
                except Exception as log_err:
                    logger.error(f"Failed to log error event: {log_err}")

            return False, None

    def reset(self):
        """Reset circuit breaker to closed state"""
        self.state = self.STATE_CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        logger.info(f"{self.component}: Circuit breaker manually reset")


class GracefulDegradation:
    """
    Graceful degradation handler for non-critical components
    Allows system to continue operating with reduced functionality
    """

    def __init__(self, component: str, fallback_value: Any = None):
        """
        Initialize graceful degradation handler

        Args:
            component: Component name for logging
            fallback_value: Default value to return on failure
        """
        self.component = component
        self.fallback_value = fallback_value
        self.is_degraded = False

    def try_with_fallback(
        self,
        func: Callable,
        *args,
        critical: bool = False,
        **kwargs
    ) -> Any:
        """
        Try to execute function, return fallback value on failure

        Args:
            func: Function to execute
            *args: Positional arguments
            critical: If True, re-raise exceptions instead of degrading
            **kwargs: Keyword arguments

        Returns:
            Function result or fallback value
        """
        try:
            result = func(*args, **kwargs)

            # If we were degraded but now succeeded, mark as recovered
            if self.is_degraded:
                logger.info(f"{self.component}: Recovered from degraded state")
                self.is_degraded = False

            return result

        except Exception as e:
            # If critical, re-raise
            if critical:
                raise

            # Mark as degraded
            if not self.is_degraded:
                logger.warning(
                    f"{self.component}: Entering degraded mode. "
                    f"Error: {str(e)}. Using fallback value: {self.fallback_value}"
                )
                self.is_degraded = True

                # Log to error database
                try:
                    error_repo = get_error_repository()
                    error_event = ErrorEvent.from_exception(
                        exception=e,
                        severity=ErrorEvent.SEVERITY_MEDIUM,
                        component=self.component,
                        message=f"Component degraded, using fallback value"
                    )
                    error_repo.log_error(error_event)
                except Exception as log_err:
                    logger.error(f"Failed to log error event: {log_err}")

            return self.fallback_value


# Global circuit breakers for common components
_circuit_breakers = {}


def get_circuit_breaker(component: str, **kwargs) -> CircuitBreaker:
    """
    Get or create circuit breaker for component

    Args:
        component: Component name
        **kwargs: Additional arguments for CircuitBreaker

    Returns:
        CircuitBreaker instance
    """
    if component not in _circuit_breakers:
        _circuit_breakers[component] = CircuitBreaker(component=component, **kwargs)
    return _circuit_breakers[component]

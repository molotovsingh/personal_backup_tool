"""
Read-Write Lock implementation for better concurrency.

This module provides a read-write lock that allows multiple concurrent readers
but exclusive write access. This improves performance for read-heavy workloads
like job status queries while maintaining thread safety for writes.

Implementation based on the "writer-preference" algorithm to prevent writer
starvation.
"""

import threading
from contextlib import contextmanager
from typing import Optional
import time
import logging

logger = logging.getLogger(__name__)


class ReadWriteLock:
    """
    A read-write lock implementation that allows multiple concurrent readers
    but exclusive write access.
    
    Features:
    - Multiple threads can hold read locks simultaneously
    - Only one thread can hold a write lock
    - Write lock requests have priority over read lock requests (writer-preference)
    - Prevents writer starvation
    - Context manager support for automatic lock release
    
    Example:
        lock = ReadWriteLock()
        
        # For reading
        with lock.read_lock():
            # Read operation
            data = get_data()
        
        # For writing
        with lock.write_lock():
            # Write operation
            set_data(new_data)
    """
    
    def __init__(self, name: Optional[str] = None):
        """
        Initialize the read-write lock.
        
        Args:
            name: Optional name for the lock (useful for debugging)
        """
        self.name = name or f"RWLock-{id(self)}"
        self._readers = 0  # Number of active readers
        self._writers = 0  # Number of active writers (0 or 1)
        self._read_ready = threading.Condition(threading.RLock())
        self._write_ready = threading.Condition(threading.RLock())
        self._pending_writers = 0  # Number of writers waiting
        
        # Statistics for monitoring
        self._read_acquisitions = 0
        self._write_acquisitions = 0
        self._max_concurrent_readers = 0
    
    def acquire_read(self, timeout: Optional[float] = None) -> bool:
        """
        Acquire a read lock.
        
        Args:
            timeout: Maximum time to wait for the lock (None for infinite)
            
        Returns:
            True if lock acquired, False if timeout
        """
        start_time = time.time()
        
        with self._read_ready:
            # Wait while there are writers or pending writers
            while self._writers > 0 or self._pending_writers > 0:
                if timeout is not None:
                    remaining = timeout - (time.time() - start_time)
                    if remaining <= 0:
                        return False
                    if not self._read_ready.wait(remaining):
                        return False
                else:
                    self._read_ready.wait()
            
            self._readers += 1
            self._read_acquisitions += 1
            self._max_concurrent_readers = max(self._max_concurrent_readers, self._readers)
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"{self.name}: Read lock acquired (readers={self._readers})")
            
            return True
    
    def release_read(self):
        """Release a read lock."""
        with self._read_ready:
            if self._readers <= 0:
                raise RuntimeError(f"{self.name}: Attempt to release read lock when no readers")
            
            self._readers -= 1
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"{self.name}: Read lock released (readers={self._readers})")
            
            # If this was the last reader, notify waiting writers
            if self._readers == 0:
                self._read_ready.notify_all()
        
        # Notify writers in their condition
        with self._write_ready:
            if self._readers == 0 and self._pending_writers > 0:
                self._write_ready.notify()
    
    def acquire_write(self, timeout: Optional[float] = None) -> bool:
        """
        Acquire a write lock.
        
        Args:
            timeout: Maximum time to wait for the lock (None for infinite)
            
        Returns:
            True if lock acquired, False if timeout
        """
        start_time = time.time()
        
        # Register as pending writer to prevent new readers
        with self._read_ready:
            self._pending_writers += 1
        
        try:
            with self._write_ready:
                # Wait while there are other writers
                while self._writers > 0:
                    if timeout is not None:
                        remaining = timeout - (time.time() - start_time)
                        if remaining <= 0:
                            return False
                        if not self._write_ready.wait(remaining):
                            return False
                    else:
                        self._write_ready.wait()
                
                # We can proceed if no other writers, mark as active writer
                self._writers = 1
                
                # Now wait for readers to finish
                with self._read_ready:
                    while self._readers > 0:
                        if timeout is not None:
                            remaining = timeout - (time.time() - start_time)
                            if remaining <= 0:
                                # Rollback writer claim
                                self._writers = 0
                                self._write_ready.notify()
                                return False
                            if not self._read_ready.wait(remaining):
                                # Rollback writer claim
                                self._writers = 0
                                self._write_ready.notify()
                                return False
                        else:
                            self._read_ready.wait()
                
                self._write_acquisitions += 1
                
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"{self.name}: Write lock acquired")
                
                return True
                
        finally:
            # Remove from pending writers
            with self._read_ready:
                self._pending_writers -= 1
                # If no more pending writers, allow readers
                if self._pending_writers == 0:
                    self._read_ready.notify_all()
    
    def release_write(self):
        """Release a write lock."""
        with self._write_ready:
            if self._writers != 1:
                raise RuntimeError(f"{self.name}: Attempt to release write lock when not held")
            
            self._writers = 0
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"{self.name}: Write lock released")
            
            # Notify waiting writers first (writer preference)
            self._write_ready.notify()
        
        # Then notify waiting readers
        with self._read_ready:
            self._read_ready.notify_all()
    
    @contextmanager
    def read_lock(self, timeout: Optional[float] = None):
        """
        Context manager for read lock.
        
        Args:
            timeout: Maximum time to wait for the lock
            
        Raises:
            TimeoutError: If lock cannot be acquired within timeout
        """
        if not self.acquire_read(timeout):
            raise TimeoutError(f"{self.name}: Failed to acquire read lock within {timeout}s")
        try:
            yield
        finally:
            self.release_read()
    
    @contextmanager
    def write_lock(self, timeout: Optional[float] = None):
        """
        Context manager for write lock.
        
        Args:
            timeout: Maximum time to wait for the lock
            
        Raises:
            TimeoutError: If lock cannot be acquired within timeout
        """
        if not self.acquire_write(timeout):
            raise TimeoutError(f"{self.name}: Failed to acquire write lock within {timeout}s")
        try:
            yield
        finally:
            self.release_write()
    
    def get_statistics(self) -> dict:
        """
        Get lock usage statistics.
        
        Returns:
            Dictionary with lock statistics
        """
        return {
            'name': self.name,
            'current_readers': self._readers,
            'current_writers': self._writers,
            'pending_writers': self._pending_writers,
            'total_read_acquisitions': self._read_acquisitions,
            'total_write_acquisitions': self._write_acquisitions,
            'max_concurrent_readers': self._max_concurrent_readers
        }
    
    def __repr__(self) -> str:
        return (f"ReadWriteLock(name={self.name}, readers={self._readers}, "
                f"writers={self._writers}, pending={self._pending_writers})")


# Global lock instance for job manager (singleton pattern)
_job_manager_lock: Optional[ReadWriteLock] = None


def get_job_manager_lock() -> ReadWriteLock:
    """
    Get the singleton job manager read-write lock.
    
    Returns:
        The global job manager lock instance
    """
    global _job_manager_lock
    if _job_manager_lock is None:
        _job_manager_lock = ReadWriteLock("JobManagerRWLock")
    return _job_manager_lock
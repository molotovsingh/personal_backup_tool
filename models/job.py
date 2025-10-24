"""
Job data model for backup jobs
"""
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class Job:
    """Represents a backup job with all necessary configuration and state"""

    # Valid job types
    TYPE_RSYNC = 'rsync'
    TYPE_RCLONE = 'rclone'
    VALID_TYPES = [TYPE_RSYNC, TYPE_RCLONE]

    # Valid job statuses
    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_PAUSED = 'paused'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    VALID_STATUSES = [STATUS_PENDING, STATUS_RUNNING, STATUS_PAUSED, STATUS_COMPLETED, STATUS_FAILED]

    def __init__(
        self,
        name: str,
        source: str,
        dest: str,
        job_type: str,
        job_id: Optional[str] = None,
        status: str = STATUS_PENDING,
        progress: Optional[Dict[str, Any]] = None,
        settings: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None
    ):
        """
        Initialize a Job

        Args:
            name: Human-readable job name
            source: Source path (local path or rclone remote)
            dest: Destination path (local path or rclone remote)
            job_type: Type of job ('rsync' or 'rclone')
            job_id: Unique identifier (generated if not provided)
            status: Current job status
            progress: Progress information dict
            settings: Job-specific settings (bandwidth_limit, etc.)
            created_at: ISO timestamp of creation
            updated_at: ISO timestamp of last update
        """
        self.id = job_id or str(uuid.uuid4())
        self.name = name
        self.source = source
        self.dest = dest
        self.type = job_type
        self.status = status
        self.progress = progress or {
            'bytes_transferred': 0,
            'total_bytes': 0,
            'percent': 0,
            'speed_bytes': 0,
            'eta_seconds': 0
        }
        self.settings = settings or {}
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()

        # Validate on initialization
        self._validate()

    def _validate(self):
        """Validate job configuration"""
        errors = []

        # Validate type
        if self.type not in self.VALID_TYPES:
            errors.append(f"Invalid job type '{self.type}'. Must be one of: {', '.join(self.VALID_TYPES)}")

        # Validate status
        if self.status not in self.VALID_STATUSES:
            errors.append(f"Invalid status '{self.status}'. Must be one of: {', '.join(self.VALID_STATUSES)}")

        # Validate name
        if not self.name or not self.name.strip():
            errors.append("Job name cannot be empty")

        # Validate source and dest
        if not self.source or not self.source.strip():
            errors.append("Source path cannot be empty")
        if not self.dest or not self.dest.strip():
            errors.append("Destination path cannot be empty")

        if errors:
            raise ValueError(f"Job validation failed: {'; '.join(errors)}")

    def validate_paths(self) -> tuple[bool, str]:
        """
        Validate that source and destination paths are valid

        Returns:
            Tuple of (is_valid, error_message)
        """
        # For rclone jobs, we can't easily validate remote paths
        # Just check that they follow remote:path format
        if self.type == self.TYPE_RCLONE:
            # Check if source or dest contain remote notation
            if ':' not in self.source and ':' not in self.dest:
                return False, "Rclone jobs must have at least one remote path (format: remote:path)"
            return True, ""

        # For rsync jobs, validate local paths
        source_path = Path(self.source)

        # Validate source exists and is readable
        if not source_path.exists():
            return False, f"Source path does not exist: {self.source}"

        if not os.access(self.source, os.R_OK):
            return False, f"Source path is not readable: {self.source}"

        # Validate destination is writable or parent directory exists
        dest_path = Path(self.dest)

        if dest_path.exists():
            # Check if writable
            if not os.access(self.dest, os.W_OK):
                return False, f"Destination path is not writable: {self.dest}"
        else:
            # Check if parent directory exists and is writable
            parent = dest_path.parent
            if not parent.exists():
                return False, f"Destination parent directory does not exist: {parent}"
            if not os.access(str(parent), os.W_OK):
                return False, f"Destination parent directory is not writable: {parent}"

        return True, ""

    def update_progress(self, progress_data: Dict[str, Any]):
        """
        Update job progress

        Args:
            progress_data: Dictionary with progress information
        """
        self.progress.update(progress_data)
        self.updated_at = datetime.now().isoformat()

    def update_status(self, new_status: str):
        """
        Update job status

        Args:
            new_status: New status value
        """
        if new_status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status '{new_status}'")

        self.status = new_status
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert Job to dictionary for serialization

        Returns:
            Dictionary representation of the job
        """
        return {
            'id': self.id,
            'name': self.name,
            'source': self.source,
            'dest': self.dest,
            'type': self.type,
            'status': self.status,
            'progress': self.progress.copy(),
            'settings': self.settings.copy(),
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Job':
        """
        Create Job from dictionary

        Args:
            data: Dictionary with job data

        Returns:
            Job instance
        """
        return Job(
            name=data['name'],
            source=data['source'],
            dest=data['dest'],
            job_type=data['type'],
            job_id=data.get('id'),
            status=data.get('status', Job.STATUS_PENDING),
            progress=data.get('progress'),
            settings=data.get('settings'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )

    def __repr__(self) -> str:
        return f"Job(id={self.id}, name='{self.name}', type={self.type}, status={self.status})"

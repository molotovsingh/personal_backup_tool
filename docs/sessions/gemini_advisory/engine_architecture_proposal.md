# Proposal: An Engine-Based Architecture for Backup Tools

This document details a proposed architectural refactoring to make the application more modular and extensible. The goal is to move from a system with hardcoded support for specific backup tools to a generic "engine-based" architecture.

## 1. The Problem

Currently, the application has specific logic for `rsync` and `rclone` embedded within its core components. If we want to add a new backup tool, such as `restic`, we would need to make significant changes to the `JobManager` and potentially other parts of the application. This approach is not scalable and makes the codebase more complex and harder to maintain over time.

## 2. The Proposal: An Engine-Based Architecture

I propose we refactor the application to use an **engine-based architecture**. This involves creating a standardized "plugin" system for backup tools.

The three main components of this architecture would be:

### a. The "Engine" Interface

We would define a standard interface, likely as a Python `abstract base class` (ABC), that all backup engines must implement. This interface will define the common methods that the core application needs to manage any backup job, regardless of the underlying tool.

**Example Interface:**

```python
# in engines/base_engine.py
from abc import ABC, abstractmethod

class BaseEngine(ABC):
    """The standard interface for all backup engines."""

    def __init__(self, job_id, job_config):
        self.job_id = job_id
        self.config = job_config

    @abstractmethod
    def run(self):
        """Start the backup process. This should be a non-blocking call."""
        pass

    @abstractmethod
    def stop(self):
        """Stop the backup process."""
        pass

    @abstractmethod
    def get_progress(self):
        """Return the current progress of the backup job."""
        pass

    @staticmethod
    @abstractmethod
    def validate_config(config):
        """Validate the configuration for a new job."""
        pass
```

### b. Concrete Engine Implementations

The existing `rsync_engine.py` and `rclone_engine.py` would be refactored to inherit from `BaseEngine` and implement the required methods. Each engine would be a self-contained module responsible for all the specific logic of its tool.

**Example `RcloneEngine`:**

```python
# in engines/rclone_engine.py
from .base_engine import BaseEngine

class RcloneEngine(BaseEngine):
    def run(self):
        # Logic to start an rclone process
        pass

    def stop(self):
        # Logic to stop the rclone process
        pass

    def get_progress(self):
        # Logic to parse rclone progress output
        pass

    @staticmethod
    def validate_config(config):
        # Logic to validate rclone source/dest paths
        pass
```

### c. A Generic `JobManager`

The `JobManager` would be refactored to be completely tool-agnostic. It would work only with the `BaseEngine` interface. Its main loop would look something like this:

1.  Get the job's `type` (e.g., "rsync", "rclone").
2.  Dynamically import the corresponding engine from the `engines/` directory (e.g., `from engines.rclone_engine import RcloneEngine`).
3.  Create an instance of that engine: `engine = RcloneEngine(job_id, job_config)`.
4.  Manage the job using the standard interface: `engine.run()`, `engine.stop()`, etc.

---

## 3. Use Case: Adding `restic`

With this new architecture, adding support for `restic` would be incredibly simple:

1.  Create a new file: `engines/restic_engine.py`.
2.  In that file, create a `ResticEngine` class that inherits from `BaseEngine`.
3.  Implement the `run`, `stop`, `get_progress`, and `validate_config` methods with the specific commands for `restic`.

**No changes would be needed to the `JobManager` or any other core application files.** The application would automatically support `restic` as a new job type.

## 4. Benefits

*   **Modularity:** The logic for each backup tool is completely isolated.
*   **Extensibility:** Adding new backup tools is a clean and predictable process.
*   **Maintainability:** The code becomes easier to understand, debug, and maintain.
*   **Testability:** Each engine can be tested independently.

## 5. Recommended Next Steps

1.  **Define and create the `BaseEngine` abstract class.**
2.  **Refactor `rsync_engine.py` and `rclone_engine.py`** to implement the `BaseEngine` interface.
3.  **Refactor the `JobManager`** to remove tool-specific logic and work with the `BaseEngine` interface.
4.  **Update the UI** to dynamically discover and display the available engine types when creating a new job.

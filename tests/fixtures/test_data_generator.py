"""
Test data generator for integration tests

Provides utilities to create test files and directories for backup testing.
"""
import os
import tempfile
import shutil
from pathlib import Path
from typing import List, Tuple
import random
import string


class TestDataGenerator:
    """Generates test files and directories for backup integration tests"""

    def __init__(self, base_dir: str = None):
        """
        Initialize test data generator

        Args:
            base_dir: Base directory for test data (defaults to temp directory)
        """
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path(tempfile.mkdtemp(prefix="backup_test_"))

        self.source_dir = self.base_dir / "source"
        self.dest_dir = self.base_dir / "dest"

        # Create base directories
        self.source_dir.mkdir(parents=True, exist_ok=True)
        self.dest_dir.mkdir(parents=True, exist_ok=True)

    def cleanup(self):
        """Remove all test data"""
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir)

    def create_file(self, path: Path, size_bytes: int, pattern: str = None):
        """
        Create a test file with specified size

        Args:
            path: Path to create file at
            size_bytes: Size of file in bytes
            pattern: Optional pattern to fill file with (default: random data)
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'wb') as f:
            if pattern:
                # Repeat pattern to fill file
                pattern_bytes = pattern.encode('utf-8')
                full_chunks = size_bytes // len(pattern_bytes)
                remainder = size_bytes % len(pattern_bytes)

                for _ in range(full_chunks):
                    f.write(pattern_bytes)
                if remainder:
                    f.write(pattern_bytes[:remainder])
            else:
                # Random data in chunks to avoid memory issues
                chunk_size = 1024 * 1024  # 1 MB chunks
                remaining = size_bytes

                while remaining > 0:
                    write_size = min(chunk_size, remaining)
                    f.write(os.urandom(write_size))
                    remaining -= write_size

    def create_small_files(self, count: int, size_range: Tuple[int, int] = (1024, 10240)) -> List[Path]:
        """
        Create multiple small test files

        Args:
            count: Number of files to create
            size_range: Tuple of (min_size, max_size) in bytes

        Returns:
            List of created file paths
        """
        files = []
        for i in range(count):
            size = random.randint(*size_range)
            filename = f"small_file_{i:04d}.txt"
            filepath = self.source_dir / filename
            self.create_file(filepath, size, pattern=f"Small file {i} content\n")
            files.append(filepath)
        return files

    def create_large_files(self, count: int, size_range: Tuple[int, int] = (10485760, 104857600)) -> List[Path]:
        """
        Create multiple large test files

        Args:
            count: Number of files to create
            size_range: Tuple of (min_size, max_size) in bytes (default: 10MB-100MB)

        Returns:
            List of created file paths
        """
        files = []
        for i in range(count):
            size = random.randint(*size_range)
            filename = f"large_file_{i:04d}.bin"
            filepath = self.source_dir / filename
            self.create_file(filepath, size)
            files.append(filepath)
        return files

    def create_directory_structure(self, depth: int = 3, files_per_dir: int = 5) -> List[Path]:
        """
        Create a nested directory structure with files

        Args:
            depth: How many levels deep to nest directories
            files_per_dir: Number of files to create in each directory

        Returns:
            List of all created file paths
        """
        files = []

        def create_level(parent: Path, current_depth: int):
            if current_depth >= depth:
                return

            # Create files at this level
            for i in range(files_per_dir):
                size = random.randint(1024, 10240)
                filename = f"file_{current_depth}_{i}.txt"
                filepath = parent / filename
                self.create_file(filepath, size, pattern=f"Level {current_depth} file {i}\n")
                files.append(filepath)

            # Create subdirectories
            num_subdirs = 2 if current_depth < depth - 1 else 0
            for i in range(num_subdirs):
                subdir = parent / f"subdir_{current_depth}_{i}"
                subdir.mkdir(parents=True, exist_ok=True)
                create_level(subdir, current_depth + 1)

        create_level(self.source_dir, 0)
        return files

    def create_files_with_special_names(self) -> List[Path]:
        """
        Create files with special characters in names (to test edge cases)

        Returns:
            List of created file paths
        """
        special_names = [
            "file with spaces.txt",
            "file-with-dashes.txt",
            "file_with_underscores.txt",
            "file.multiple.dots.txt",
            "file(with)parentheses.txt",
            "file[with]brackets.txt",
            "file'with'quotes.txt",
            "file\"with\"doublequotes.txt",
            "file&with&ampersand.txt",
            "file#with#hash.txt",
        ]

        files = []
        for name in special_names:
            filepath = self.source_dir / name
            try:
                self.create_file(filepath, 1024, pattern=f"Special name: {name}\n")
                files.append(filepath)
            except Exception:
                # Some characters may not be valid on all filesystems
                pass

        return files

    def create_mixed_dataset(self) -> dict:
        """
        Create a realistic mixed dataset with various file types and sizes

        Returns:
            Dictionary with counts and paths of created files
        """
        dataset = {
            'small_files': self.create_small_files(50, (100, 1024)),  # 50 tiny files
            'medium_files': self.create_small_files(20, (10240, 102400)),  # 20 medium files
            'large_files': self.create_large_files(5, (1048576, 10485760)),  # 5 large files (1-10MB)
            'special_names': self.create_files_with_special_names(),
            'nested_structure': self.create_directory_structure(depth=3, files_per_dir=3),
        }

        return dataset

    def get_total_size(self, directory: Path = None) -> int:
        """
        Calculate total size of all files in a directory

        Args:
            directory: Directory to calculate (defaults to source_dir)

        Returns:
            Total size in bytes
        """
        if directory is None:
            directory = self.source_dir

        total = 0
        for item in directory.rglob('*'):
            if item.is_file():
                total += item.stat().st_size
        return total

    def get_file_count(self, directory: Path = None) -> int:
        """
        Count total number of files in a directory

        Args:
            directory: Directory to count (defaults to source_dir)

        Returns:
            Number of files
        """
        if directory is None:
            directory = self.source_dir

        return sum(1 for item in directory.rglob('*') if item.is_file())

    def verify_backup(self, source: Path = None, dest: Path = None) -> Tuple[bool, str]:
        """
        Verify that backup matches source

        Args:
            source: Source directory (defaults to source_dir)
            dest: Destination directory (defaults to dest_dir)

        Returns:
            Tuple of (success, message)
        """
        if source is None:
            source = self.source_dir
        if dest is None:
            dest = self.dest_dir

        # Get all files in source
        source_files = {
            f.relative_to(source): f
            for f in source.rglob('*')
            if f.is_file()
        }

        # Get all files in dest
        dest_files = {
            f.relative_to(dest): f
            for f in dest.rglob('*')
            if f.is_file()
        }

        # Check if all source files exist in dest
        missing_files = set(source_files.keys()) - set(dest_files.keys())
        if missing_files:
            return False, f"Missing files in destination: {list(missing_files)[:5]}"

        # Check if there are extra files in dest
        extra_files = set(dest_files.keys()) - set(source_files.keys())
        if extra_files:
            return False, f"Extra files in destination: {list(extra_files)[:5]}"

        # Verify file sizes match
        for rel_path in source_files:
            source_size = source_files[rel_path].stat().st_size
            dest_size = dest_files[rel_path].stat().st_size

            if source_size != dest_size:
                return False, f"Size mismatch for {rel_path}: source={source_size}, dest={dest_size}"

        return True, f"Backup verified: {len(source_files)} files match"

    def corrupt_file(self, filepath: Path, corruption_percent: float = 0.1):
        """
        Intentionally corrupt a file (for testing verification)

        Args:
            filepath: File to corrupt
            corruption_percent: Percentage of file to corrupt (0.0-1.0)
        """
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        size = filepath.stat().st_size
        if size == 0:
            return

        # Calculate how many bytes to corrupt
        corrupt_bytes = max(1, int(size * corruption_percent))

        # Read file
        with open(filepath, 'rb') as f:
            data = bytearray(f.read())

        # Corrupt random positions
        for _ in range(corrupt_bytes):
            pos = random.randint(0, len(data) - 1)
            data[pos] = random.randint(0, 255)

        # Write corrupted data
        with open(filepath, 'wb') as f:
            f.write(data)

    def simulate_partial_transfer(self, files: List[Path], percent_complete: int = 50):
        """
        Simulate a partial transfer by copying only some files to dest

        Args:
            files: List of files to partially copy
            percent_complete: Percentage of files to copy (0-100)
        """
        num_to_copy = max(1, int(len(files) * percent_complete / 100))
        files_to_copy = random.sample(files, num_to_copy)

        for src_file in files_to_copy:
            rel_path = src_file.relative_to(self.source_dir)
            dest_file = self.dest_dir / rel_path
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dest_file)


def create_test_scenario(scenario_type: str) -> TestDataGenerator:
    """
    Create a predefined test scenario

    Args:
        scenario_type: Type of scenario ('small', 'large', 'mixed', 'nested')

    Returns:
        TestDataGenerator with scenario data
    """
    gen = TestDataGenerator()

    if scenario_type == 'small':
        # Many small files
        gen.create_small_files(100, (100, 10240))

    elif scenario_type == 'large':
        # Few large files
        gen.create_large_files(10, (10485760, 52428800))  # 10-50MB each

    elif scenario_type == 'mixed':
        # Realistic mixed dataset
        gen.create_mixed_dataset()

    elif scenario_type == 'nested':
        # Deep directory structure
        gen.create_directory_structure(depth=5, files_per_dir=3)

    else:
        raise ValueError(f"Unknown scenario type: {scenario_type}")

    return gen


if __name__ == '__main__':
    # Example usage
    gen = create_test_scenario('mixed')
    print(f"Created test data in: {gen.base_dir}")
    print(f"Total files: {gen.get_file_count()}")
    print(f"Total size: {gen.get_total_size() / 1024 / 1024:.2f} MB")
    print("\nTo clean up, run: gen.cleanup()")

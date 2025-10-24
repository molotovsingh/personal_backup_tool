#!/bin/bash
# Installation script for Backup Manager

echo "=================================="
echo "Backup Manager - Installation"
echo "=================================="
echo ""

# Check Python
echo "Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo "✓ Python $PYTHON_VERSION found"
else
    echo "✗ Python 3 not found. Please install Python 3.9+"
    exit 1
fi

# Check uv
echo ""
echo "Checking uv..."
if command -v uv &> /dev/null; then
    echo "✓ uv found"
else
    echo "✗ uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Create venv
echo ""
echo "Creating virtual environment..."
uv venv
echo "✓ Virtual environment created"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
uv pip install -r requirements.txt
echo "✓ Python dependencies installed"

# Check watchdog (optional dev dependency)
echo ""
echo "Checking optional development dependencies..."
if python3 -c "import watchdog" 2>/dev/null; then
    echo "✓ watchdog is installed (faster auto-reload)"
else
    echo "ℹ watchdog not installed (optional)"
    echo "  For better development performance:"
    echo "  uv pip install -r requirements-dev.txt"
fi

# Check rsync
echo ""
echo "Checking system dependencies..."
if command -v rsync &> /dev/null; then
    echo "✓ rsync is installed"
else
    echo "⚠ rsync not found"
    echo "  Install with: brew install rsync (macOS)"
fi

# Check rclone
if command -v rclone &> /dev/null; then
    echo "✓ rclone is installed"
else
    echo "⚠ rclone not found (optional, for cloud storage)"
    echo "  Install with: brew install rclone (macOS)"
    echo "  Then run: rclone config"
fi

echo ""
echo "=================================="
echo "Installation Complete!"
echo "=================================="
echo ""
echo "To start the app:"
echo "  uv run streamlit run app.py"
echo ""
echo "To configure your backup jobs:"
echo "  uv run setup_jobs.py"
echo ""

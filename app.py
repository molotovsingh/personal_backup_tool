#!/usr/bin/env python3
"""
Streamlit UI has been retired.

The backup-manager application now uses Flask for better performance
and scalability. Please use the Flask application instead.

Quick Start:
  uv run python flask_app.py

The Flask app will be available at:
  http://localhost:5001

For more information, see:
  - FLASK_MIGRATION_COMPLETE.md
  - README.md

The original Streamlit app is archived in:
  archive/streamlit/app.py
"""
import sys

def main():
    print(__doc__)
    print("\n" + "="*70)
    print("ERROR: Streamlit UI retired - Use Flask instead")
    print("="*70)
    print("\nRun this command to start the Flask app:")
    print("  uv run python flask_app.py")
    print()
    sys.exit(1)

if __name__ == "__main__":
    main()

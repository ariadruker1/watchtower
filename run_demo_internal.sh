#!/bin/bash
# Internal script called by run_demo.sh - runs the Python demo

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Get the project root (parent of watchtower_mvp)
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to the project root so imports work correctly
cd "$PROJECT_ROOT"

# Run the Python demo directly
python3 watchtower_mvp/step_through_demo.py

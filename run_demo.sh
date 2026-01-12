#!/bin/bash
# Launch the step-through demo in a new terminal window

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the watchtower_mvp directory
cd "$SCRIPT_DIR"

# Open in a new terminal window (macOS)
open -a Terminal "$SCRIPT_DIR/run_demo_internal.sh"

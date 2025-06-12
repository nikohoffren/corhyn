#!/bin/bash

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the package in development mode
pip install -e .

echo "TaskMaster has been installed successfully!"
echo "You can now use it by running 'taskmaster' in your terminal."
echo "Try 'taskmaster --help' to see available commands."

#!/bin/bash

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the package in development mode
pip install -e .

echo "Corhyn CLI has been installed successfully!"
echo "You can now use it by running 'corhyn' in your terminal."
echo "Try 'corhyn --help' to see available commands."

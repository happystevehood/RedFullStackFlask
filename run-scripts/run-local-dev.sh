#!/bin/bash
# Run the application locally in development mode

# Set environment variables
export ENV_MODE=development

# Change to the src directory
cd "$(dirname "$0")/../src"

# Run the application
python app.py
#!/bin/bash
# Run the application locally in production mode

# Set environment variables
export ENV_MODE=production

# Change to the src directory
cd "$(dirname "$0")/../src"

# Run the application
python app.py
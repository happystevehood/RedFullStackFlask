#!/bin/bash
# Run the application in Docker in development mode

# Set environment variables
export ENV_FILE=.env.development
export ENV_MODE=development
export USE_DOCKER=True
export PORT=5000

# Change to the project root directory
cd "$(dirname "$0")/.."

# Run the application with Docker Compose
docker-compose down
docker-compose up --build
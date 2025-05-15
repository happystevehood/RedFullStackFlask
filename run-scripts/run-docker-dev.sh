#!/bin/bash
# Run the application in Docker in development mode

#docker desktop needs to be open to run this script.

# Set environment variables
export ENV_FILE=.env.development
export ENV_MODE=development
export PORT=5000

# Change to the project root directory
cd "$(dirname "$0")/.."

# Run the application with Docker Compose
docker-compose down
docker-compose up --build
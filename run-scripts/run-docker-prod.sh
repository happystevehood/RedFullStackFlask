#!/bin/bash
# Run the application in Docker in production mode

# Set environment variables
export ENV_FILE=.env.production
export ENV_MODE=production
export PORT=8080

# Change to the project root directory
cd "$(dirname "$0")/.."

#docker desktop needs to be open to run this script.

# Run the application with Docker Compose
docker-compose -f docker-compose-local.yml down
docker-compose -f docker-compose-local.yml up --build
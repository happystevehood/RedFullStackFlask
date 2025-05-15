#!/bin/bash
# Deploy the application to a production server 

export IMAGE=gcr.io/redline-fitness-results/app.py:latest

# Set environment variables
export ENV_FILE=.env.deploy
export ENV_MODE=deploy
export PORT=8080


# Change to the project root directory
cd "$(dirname "$0")/.."

#Build your Docker image
docker build -f Dockerfile_deploy -t $IMAGE .
#!/bin/bash
# Deploy the application to a production server 

export NAME_VERSION=v4.26
export PROJECT_ID=redline-fitness-results
export IMAGE=gcr.io/$PROJECT_ID/app.py:$NAME_VERSION
#export IMAGE=gcr.io/$PROJECT_ID/app_test.py:$NAME_VERSION

# Set environment variables
export ENV_FILE=.env.deploy
export ENV_MODE=deploy
export PORT=8080


# Change to the project root directory
cd "$(dirname "$0")/.."

#Build your Docker image
#docker build --no-cache -f Dockerfile_deploy -t $IMAGE .
docker build -f Dockerfile_deploy -t $IMAGE .
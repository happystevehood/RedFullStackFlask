# Run Scripts

This directory contains scripts to run the application in different scenarios.

## Available Scenarios

1. **Local Development** - Run the app locally without Docker in development mode
2. **Local Production** - Run the app locally without Docker in production mode
3. **Docker Development** - Run the app in Docker in development mode
4. **Docker Production** - Run the app in Docker in production mode
5. **Build Deploy** - Build the app in docker in preparation for deployment to gcloud
6. **Push Run Deploy** - Push to gcr.io and run using Google Cloud Run
6. **gcloud setup** - All commented out, but left some commands which helped with authentication with gcr.io, and setting up a gcloud bucket

## Usage

### On Linux/Mac

Use the `.sh` files:

```
./run-scripts/run-local-dev.sh
./run-scripts/run-local-prod.sh
./run-scripts/run-docker-dev.sh
./run-scripts/run-docker-prod.sh
./run-scripts/build-deploy-prod.sh
./run-scripts/push-run-deploy-prod.sh
./run-scripts/gcloud-setup

#!/bin/bash
# Deploy docker image to the gcloud platform 

export IMAGE=gcr.io/redline-fitness-results/app.py:latest

#Change to the project root directory
cd "$(dirname "$0")/.."

#Push your Docker image to Google Container Registry
docker push  $IMAGE

#Deploy to Cloud Run
#currently deploying manually via site
#gcloud run deploy redline-results --image $IMAGE --platform managed --region asia-southeast1 --allow-unauthenticated --memory 1024M --service-account=$SERVICE_ACCOUNT

#Set environment variables in the app gcloud run service itself
#   --set-env-vars "ADMIN_PASSWORD=VALUE1" \
#   --set-env-vars "SECRET_KEY=VALUE2" \

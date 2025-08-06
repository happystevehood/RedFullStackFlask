#!/bin/bash
# Deploy docker image to the gcloud platform 

export NAME_VERSION=v4.26
export PROJECT_ID=redline-fitness-results
export IMAGE=gcr.io/$PROJECT_ID/app.py:$NAME_VERSION
#export IMAGE=gcr.io/$PROJECT_ID/app_test.py:$NAME_VERSION

#Change to the project root directory
cd "$(dirname "$0")/.."

#Push your Docker image to Google Container Registry
docker push  $IMAGE

#Deploy to Cloud Run
#currently deploying manually via site, initially used command belwo
#gcloud run deploy redline-results --image $IMAGE --platform managed --region asia-southeast1 --allow-unauthenticated --memory 1024M --service-account=$SERVICE_ACCOUNT

#!/bin/bash
# Deploy to the gcloud platform from google cloud shell

#Change to the project root directory
cd "$(dirname "$0")/.."

#Needed if issue with gcr.io permissions - only once?
#gcloud auth configure-docker gcr.io

#Need to configure-docker for google cloud - only once?
#gcloud auth print-access-token | docker login -u oauth2accesstoken --password-stdin https://gcr.io

#Push your Docker image to Google Container Registry
docker push  gcr.io/redline-fitness-results/app.py:latest

#Deploy to Cloud Run
gcloud run deploy redline-results --image gcr.io/redline-fitness-results/app.py:latest --platform managed --region asia-southeast1 --allow-unauthenticated --memory 1024M

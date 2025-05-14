#!/bin/bash
# Deploy to the gcloud platform from google cloud shell

#Change to the project root directory
cd "$(dirname "$0")/.."

#Needed if issue with gcr.io permissions - only once?
#gcloud auth configure-docker gcr.io

#Need to configure-docker for google cloud - only once?
#gcloud auth print-access-token | docker login -u oauth2accesstoken --password-stdin https://gcr.io

#To grant the Cloud Run service identity the "Storage Object Admin" role directly on the bucket -only once?
gcloud projects add-iam-policy-binding redline-fitness-results --member="serviceAccount:951032250531-compute@developer.gserviceaccount.com" --role="roles/storage.objectAdmin"

#Create a Workload Identity Pool and Provider:
gcloud iam workload-identity-pools create redline-storage-pool --location="global" --description="Workload Identity Pool for Redline Storage App"
gcloud iam workload-identity-pools providers create-oidc "redline-storage-provider" --location="global" --workload-identity-pool="redline-storage-pool" --issuer-uri="https://iam.googleapis.com" --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor"

#Grant the Cloud Run Service Account Permissions to the Pool:
#didnt work#gcloud iam workload-identity-pools add-iam-policy-binding redline-storage-pool --location="global" --member="serviceAccount:951032250531-compute@developer.gserviceaccount.com" --role="roles/iam.workloadIdentityUser"    
gcloud projects add-iam-policy-binding redline-fitness-results --role="roles/iam.workloadIdentityUser" --member="serviceAccount:951032250531-compute@developer.gserviceaccount.com" --condition=None

#Push your Docker image to Google Container Registry
docker push  gcr.io/redline-fitness-results/app.py:latest

#Deploy to Cloud Run
#gcloud run deploy redline-results --image gcr.io/redline-fitness-results/app.py:latest --platform managed --region asia-southeast1 --allow-unauthenticated --memory 1024M
gcloud run deploy redline-results --image gcr.io/redline-fitness-results/app.py:latest --platform managed --region asia-southeast1 --allow-unauthenticated --memory 1024M --service-account=951032250531-compute@developer.gserviceaccount.com



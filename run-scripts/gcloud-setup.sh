#!/bin/bash
# Deploy to the gcloud platform from google cloud shell

#
#Below this line which were used to setup auth with gcr.io
#

#Needed if issue with gcr.io permissions 
#gcloud auth configure-docker gcr.io

#Need to configure-docker for google cloud 
#gcloud auth print-access-token | docker login -u oauth2accesstoken --password-stdin https://gcr.io

#
#Below this line were commands which were used to setup a gcloud bitbucket.
#

#To grant the Cloud Run service identity the "Storage Object Admin" role directly on the bucket 
#gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT" --role="roles/storage.objectAdmin"

#Create a Workload Identity Pool and Provider:
#gcloud iam workload-identity-pools create redline-storage-pool --location="global" --description="Workload Identity Pool for Redline Storage App"
#gcloud iam workload-identity-pools providers create-oidc "redline-storage-provider" --location="global" --workload-identity-pool="redline-storage-pool" --issuer-uri="https://iam.googleapis.com" --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor"

#Grant the Cloud Run Service Account Permissions to the Pool:
#gcloud projects add-iam-policy-binding $PROJECT_ID --role="roles/iam.workloadIdentityUser" --member="$SERVICE_ACCOUNT" --condition=None

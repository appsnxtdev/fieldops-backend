#!/bin/bash
set -e

PROJECT_ID=$(gcloud config get-value project)
REGION="asia-southeast1"
SERVICE_NAME="fieldops-backend"
IMAGE_NAME="asia-southeast1-docker.pkg.dev/${PROJECT_ID}/fieldops-backend/${SERVICE_NAME}"

echo "Building and pushing image..."
gcloud builds submit --tag ${IMAGE_NAME}:latest

echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME}:latest \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --port 8000 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0 \
  --set-env-vars="ENVIRONMENT=production,SUPABASE_URL=https://inakqzvnfevykqkcotvb.supabase.co,CORE_SERVICE_URL=https://api.appnxt.cloud,UPSTASH_REDIS_REST_URL=https://perfect-cowbird-74094.upstash.io,ALLOWED_ORIGINS=https://fieldops.appsnxt.cloud,https://saas.appsnxt.cloud" \
  --set-secrets="SUPABASE_DB_PASSWORD=supabase-db-password:latest,SUPABASE_SERVICE_ROLE_KEY=supabase-service-role-key:latest,SUPABASE_JWT_SECRET=supabase-jwt-secret:latest,UPSTASH_REDIS_REST_TOKEN=upstash-redis-rest-token:latest"

echo "Deployment complete!"
echo "Service URL: $(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')"
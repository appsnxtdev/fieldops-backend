#!/usr/bin/env bash
set -e

PROJECT_ID=$(gcloud config get-value project)
REGION="asia-southeast1"
SERVICE_NAME="fieldops-backend"
IMAGE_NAME="asia-southeast1-docker.pkg.dev/${PROJECT_ID}/${SERVICE_NAME}/${SERVICE_NAME}"

# Optional: pass env from .env (excludes PORT and comments)
ENV_ARGS=()
if [[ -f .env ]]; then
  while IFS= read -r line; do
    [[ "$line" =~ ^#.*$ || -z "$line" || "$line" =~ ^PORT= ]] && continue
    ENV_ARGS+=(--set-env-vars "$line")
  done < .env
fi

echo "Building and pushing image..."
gcloud builds submit --tag "${IMAGE_NAME}:latest"

echo "Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE_NAME}:latest" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0 \
  "${ENV_ARGS[@]}"

echo "Deployment complete!"
echo "Service URL: $(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')"

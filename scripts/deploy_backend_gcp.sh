#!/bin/sh
set -eu

: "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
: "${GCP_REGION:?Set GCP_REGION}"
: "${AR_REPO:?Set AR_REPO}"
: "${CLOUD_RUN_SERVICE:?Set CLOUD_RUN_SERVICE}"
: "${CLOUD_SQL_CONNECTION_NAME:?Set CLOUD_SQL_CONNECTION_NAME}"
: "${DATABASE_URL:?Set DATABASE_URL}"

IMAGE_URI="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${AR_REPO}/${CLOUD_RUN_SERVICE}"
ENV_VARS="DATABASE_URL=${DATABASE_URL}"

if [ "${RUN_SEED_ON_STARTUP:-false}" = "true" ]; then
  ENV_VARS="${ENV_VARS},RUN_SEED_ON_STARTUP=true"
fi

gcloud builds submit ./backend --tag "${IMAGE_URI}"

gcloud run deploy "${CLOUD_RUN_SERVICE}" \
  --image "${IMAGE_URI}" \
  --region "${GCP_REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --add-cloudsql-instances "${CLOUD_SQL_CONNECTION_NAME}" \
  --set-env-vars "${ENV_VARS}"

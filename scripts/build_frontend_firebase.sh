#!/bin/sh
set -eu

: "${VITE_API_BASE_URL:?Set VITE_API_BASE_URL}"

cd frontend
npm ci
VITE_API_BASE_URL="${VITE_API_BASE_URL}" npm run build

#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Task 10: build-and-push.sh
# Builds Docker images and pushes them to a registry.
# Usage: bash scripts/build-and-push.sh --registry localhost:5000 --tag 1.0.0
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
CYAN='\033[0;36m'; GREEN='\033[0;32m'; NC='\033[0m'

log() { echo -e "${CYAN}[BUILD]${NC} $*"; }
ok()  { echo -e "${GREEN}[OK]${NC}    $*"; }

REGISTRY="${REGISTRY:-localhost:5000}"
TAG="${TAG:-latest}"
PLATFORMS="${PLATFORMS:-linux/amd64}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --registry) REGISTRY="$2"; shift 2 ;;
    --tag)      TAG="$2";      shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

AI_MODEL_IMAGE="${REGISTRY}/ai-chat/ai-model:${TAG}"
FRONTEND_IMAGE="${REGISTRY}/ai-chat/frontend:${TAG}"

log "Building ai-model → ${AI_MODEL_IMAGE}"
docker build \
  --platform "$PLATFORMS" \
  --build-arg BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --build-arg GIT_COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)" \
  -t "$AI_MODEL_IMAGE" \
  -t "${REGISTRY}/ai-chat/ai-model:latest" \
  ./ai-model
ok "ai-model built"

log "Building frontend → ${FRONTEND_IMAGE}"
docker build \
  --platform "$PLATFORMS" \
  -t "$FRONTEND_IMAGE" \
  -t "${REGISTRY}/ai-chat/frontend:latest" \
  ./frontend
ok "frontend built"

log "Pushing images to ${REGISTRY}…"
docker push "$AI_MODEL_IMAGE"
docker push "${REGISTRY}/ai-chat/ai-model:latest"
docker push "$FRONTEND_IMAGE"
docker push "${REGISTRY}/ai-chat/frontend:latest"

ok "═══════════════════════════════════════"
ok "Pushed:"
ok "  ${AI_MODEL_IMAGE}"
ok "  ${FRONTEND_IMAGE}"
ok "═══════════════════════════════════════"

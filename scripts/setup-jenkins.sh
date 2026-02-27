#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Task 10: setup-jenkins.sh
# Starts Jenkins + local registry, prints setup instructions.
# Usage: bash scripts/setup-jenkins.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

log()  { echo -e "${CYAN}[JENKINS]${NC} $*"; }
ok()   { echo -e "${GREEN}[OK]${NC}      $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}    $*"; }

log "Starting Jenkins stack…"
docker compose -f jenkins/docker-compose.yml up -d

log "Waiting for Jenkins to initialise (this takes ~60s on first run)…"
until curl -sf http://localhost:8080/login >/dev/null 2>&1; do
  printf "."
  sleep 5
done
echo ""
ok "Jenkins is up!"

ADMIN_PASS=$(docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword 2>/dev/null || echo "<not found yet – try again in 30s>")

echo ""
ok "══════════════════════════════════════════════════════════"
ok "Jenkins UI:     http://localhost:8080"
ok "Admin password: ${ADMIN_PASS}"
ok ""
ok "Required Jenkins plugins to install:"
ok "  - Pipeline"
ok "  - Git"
ok "  - Docker Pipeline"
ok "  - Kubernetes CLI"
ok "  - Credentials Binding"
ok "  - Blue Ocean (optional, for better UI)"
ok ""
ok "Configure credentials in Jenkins → Manage → Credentials:"
ok "  ID: 'docker-registry-credentials' (Username/Password)"
ok "  ID: 'kubeconfig'                  (Secret File – your ~/.kube/config)"
ok ""
ok "Local registry: http://localhost:5000"
ok "Use as: localhost:5000/ai-chat/ai-model:latest"
ok "══════════════════════════════════════════════════════════"

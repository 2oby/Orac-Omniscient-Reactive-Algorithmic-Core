#!/usr/bin/env bash
set -euo pipefail

# Usage: ./deploy_and_test.sh [commit_message] [branch] [service_name]
COMMIT_MSG=${1:-"Update ORAC MVP"}
DEPLOY_BRANCH=${2:-"mvp"}
SERVICE_NAME=${3:-"orac"}   # Docker Compose service to exec into
REMOTE_ALIAS="orin"
SSH_ORIGIN="git@github.com:2oby/Orac-Omniscient-Reactive-Algorithmic-Core.git"

echo "👉  Pushing local commits to '$DEPLOY_BRANCH'..."

# 1) Local: switch, pull, commit, push
current_branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$current_branch" != "$DEPLOY_BRANCH" ]; then
  git checkout "$DEPLOY_BRANCH"
fi

git pull origin "$DEPLOY_BRANCH"
git add .
if ! git diff --cached --quiet; then
  git commit -m "$COMMIT_MSG"
fi
git push origin "$DEPLOY_BRANCH"

# 2) Remote: pull, build & test in container
echo "👉  Running remote update & tests on $REMOTE_ALIAS..."
ssh "$REMOTE_ALIAS" "\
  set -euo pipefail; \
  cd \$HOME/ORAC; \
  git remote set-url origin $SSH_ORIGIN || true; \
  git fetch origin; \
  if git show-ref --verify --quiet refs/heads/$DEPLOY_BRANCH; then \
    git checkout $DEPLOY_BRANCH; \
  else \
    git checkout -b $DEPLOY_BRANCH origin/$DEPLOY_BRANCH; \
  fi; \
  git pull origin $DEPLOY_BRANCH; \
  if command -v docker compose &> /dev/null; then \
    DOCKER_CMD='docker compose'; \
  else \
    DOCKER_CMD='docker-compose'; \
  fi; \
  echo '🐳 Building & starting containers...'; \
  \$DOCKER_CMD up --build -d; \
  echo '🧪 Running pytest inside container \"$SERVICE_NAME\"...'; \
  \$DOCKER_CMD exec -T $SERVICE_NAME pytest -q tests/ --ignore=archive/legacy; \

"

echo "🎉 Deployment + remote tests inside '$SERVICE_NAME' succeeded!"

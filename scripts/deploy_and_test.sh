#!/usr/bin/env bash
set -euo pipefail

# Usage: ./deploy_and_test.sh [commit_message] [branch]
COMMIT_MSG=${1:-"Update ORAC MVP"}
DEPLOY_BRANCH=${2:-"mvp"}
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

# 2) Remote: pull, build & test
echo "👉  Running remote update & tests on $REMOTE_ALIAS..."
ssh "$REMOTE_ALIAS" "\
  set -euo pipefail; \
  cd \$HOME/ORAC; \
  echo '💡 Before set-url:' \$(git remote get-url origin); \
  git remote set-url origin $SSH_ORIGIN; \
  echo '💡 After  set-url:' \$(git remote get-url origin); \
  echo '💡 Fetching & checking out $DEPLOY_BRANCH...'; \
  git fetch origin; \
  if git show-ref --verify --quiet refs/heads/$DEPLOY_BRANCH; then \
    git checkout $DEPLOY_BRANCH; \
  else \
    git checkout -b $DEPLOY_BRANCH origin/$DEPLOY_BRANCH; \
  fi; \
  git pull origin $DEPLOY_BRANCH; \
  echo '🐳 Building & starting containers...'; \
  if command -v docker compose &> /dev/null; then \
    docker compose up --build -d; \
  else \
    docker-compose up --build -d; \
  fi; \
  echo '🧪 Running pytest...'; \
  pytest -q \
"

echo "🎉 Deployment + remote tests succeeded!"

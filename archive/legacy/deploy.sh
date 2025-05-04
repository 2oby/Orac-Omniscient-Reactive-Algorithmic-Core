#!/usr/bin/env bash
set -euo pipefail

# Usage: ./deploy.sh [commit_message] [branch]
COMMIT_MSG=${1:-"Update ORAC MVP"}
DEPLOY_BRANCH=${2:-"mvp"}
REMOTE_ALIAS="orin"
REMOTE_PATH="$HOME/ORAC"
SSH_ORIGIN="git@github.com:2oby/Orac-Omniscient-Reactive-Algorithmic-Core.git"

echo "🛠  Deploying branch '$DEPLOY_BRANCH' with message: $COMMIT_MSG"

# —————————————————————————————————————————————————————————————
# 1) Local: ensure on the right branch, pull, commit & push
# —————————————————————————————————————————————————————————————

current_branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$current_branch" != "$DEPLOY_BRANCH" ]; then
  echo "🔀 Switching local branch '$current_branch' → '$DEPLOY_BRANCH'"
  git checkout "$DEPLOY_BRANCH"
fi

echo "⬇️  Pulling latest locally..."
git pull origin "$DEPLOY_BRANCH"

echo "➕ Staging changes..."
git add .

if git diff --cached --quiet; then
  echo "✅ No local changes to commit."
else
  echo "💬 Committing with message: $COMMIT_MSG"
  git commit -m "$COMMIT_MSG"
fi

echo "🚀 Pushing to origin/$DEPLOY_BRANCH..."
git push origin "$DEPLOY_BRANCH"

# —————————————————————————————————————————————————————————————
# 2) Remote: set SSH origin, fetch, checkout, pull, build & test
# —————————————————————————————————————————————————————————————

echo "🌐 Deploying & testing on remote '$REMOTE_ALIAS'..."
ssh "$REMOTE_ALIAS" bash <<EOF
  set -euo pipefail

  cd "$REMOTE_PATH"

  echo "🔑 Ensuring Git origin uses SSH URL"
  git remote set-url origin "$SSH_ORIGIN" || true

  echo "⬇️ Fetching origin"
  git fetch origin

  # If branch exists locally, switch, otherwise create tracking branch
  if git show-ref --verify --quiet refs/heads/$DEPLOY_BRANCH; then
    echo "🔀 Checking out existing branch '$DEPLOY_BRANCH'"
    git checkout "$DEPLOY_BRANCH"
  else
    echo "🔀 Creating & tracking branch '$DEPLOY_BRANCH'"
    git checkout -b "$DEPLOY_BRANCH" "origin/$DEPLOY_BRANCH"
  fi

  echo "⬇️ Pulling latest on '$DEPLOY_BRANCH'"
  git pull origin "$DEPLOY_BRANCH"

  echo "🐳 Building & starting containers"
  if command -v docker compose &> /dev/null; then
    docker compose up --build -d
  else
    docker-compose up --build -d
  fi

  echo "🧪 Running pytest (remote output follows)"
  pytest -q
EOF

echo "🎉 Deployment + remote tests succeeded!"

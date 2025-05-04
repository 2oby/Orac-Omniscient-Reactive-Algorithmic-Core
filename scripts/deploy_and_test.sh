#!/usr/bin/env bash
set -euo pipefail

# --- user‑editable variables -----------------------------------------------
JETSON_HOST="orin"          # your SSH alias in ~/.ssh/config
PROJECT_DIR="~/ORAC"        # path on the Jetson where the repo lives
BRANCH="mvp"                # branch to deploy & test
# ---------------------------------------------------------------------------

echo "👉  Pushing local commits..."
git push -u origin "${BRANCH}"

echo "👉  Running remote update & tests on ${JETSON_HOST} ..."
ssh "${JETSON_HOST}" bash - <<EOF
  set -euo pipefail
  cd ${PROJECT_DIR}
  echo "💡 pulling latest ${BRANCH} ..."
  git checkout ${BRANCH}
  git pull --ff-only

  echo "⬇ installing test deps (pytest, respx)..."
  python3 -m pip install --user --quiet pytest respx httpx

  echo "🧪 running tests ..."
  pytest -q
EOF

echo "✅  Remote tests passed on ${JETSON_HOST}"


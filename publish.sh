#!/usr/bin/env bash
# Rebuild the dashboard and publish to GitHub Pages — but ONLY when a live input
# (results/odds) actually changed. The model uses fixed RNG seeds, so rebuilding
# with no new data only churns the "generated" timestamp; we skip that so the
# public site and git history stay clean and we don't trigger no-op deploys.
#
# Usage:  bash publish.sh "short summary of what changed"
# Assumes the caller already pulled latest and wrote any new data into
# results_log.json / odds.json / match_odds.json.
set -euo pipefail
cd "$(dirname "$0")"

INPUTS="results_log.json odds.json match_odds.json"
OUTPUTS="results.json version.json index.html World_Cup_2026_Predictor.html"

if git diff --quiet -- $INPUTS; then
  echo "No input changes (results/odds) since last build — nothing to publish."
  # discard any stray rebuilt outputs so the working tree stays clean
  git checkout -- $OUTPUTS 2>/dev/null || true
  exit 0
fi

echo "New input data detected — rebuilding…"
python3 build.py && python3 gen_dashboard.py

# Stage ONLY the data inputs and generated outputs — never `git add -A`, which would
# sweep unrelated working-tree edits (e.g. in-progress code changes) into this unattended
# auto-commit and push them, unreviewed, to the live site.
git add $INPUTS $OUTPUTS
git commit -m "Auto rebuild: ${1:-results/odds update} ($(date -u +%Y-%m-%dT%H:%MZ))"
git push origin main
echo "Published. GitHub Pages will redeploy within ~1 minute:"
echo "  https://milanpcooper-ui.github.io/world-cup-2026-bracket-model/"

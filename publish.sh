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

echo "New input data detected — validating…"
# Hard gate: validate the inputs BEFORE building or committing. This rejects
# malformed data and, critically, any result for a game that cannot have finished
# yet (the kickoff-time gate in validate_inputs.py / schedule_gate.py) — so a
# fabricated/premature score can never reach the live site.
#
# On failure we REVERT the input edits to the last committed state and abort. That
# is deliberate: a rejected input is invalid by definition, and leaving the bad
# edit in a tracked file would make the next unattended run's `git pull --rebase`
# fail on a dirty tree and wedge the whole 3-hourly loop. Reverting keeps the tree
# clean so the next run self-heals. The "WC26-PUBLISH-ABORTED" marker is greppable
# in run.log (validate exits inside the agent's turn, so its non-zero code does not
# propagate to the launchd run — detect this failure by content, not exit code).
if ! python3 validate_inputs.py; then
  echo "WC26-PUBLISH-ABORTED: input validation failed — see errors above."
  echo "Reverting input edits ($INPUTS) to the last committed state to keep the"
  echo "working tree clean (a leftover bad edit would wedge the next auto-run)."
  git checkout HEAD -- $INPUTS
  exit 1
fi

echo "Inputs valid — rebuilding…"
python3 build.py && python3 gen_dashboard.py

# Stage ONLY the data inputs and generated outputs — never `git add -A`, which would
# sweep unrelated working-tree edits (e.g. in-progress code changes) into this unattended
# auto-commit and push them, unreviewed, to the live site.
git add $INPUTS $OUTPUTS
git commit -m "Auto rebuild: ${1:-results/odds update} ($(date -u +%Y-%m-%dT%H:%MZ))"
git push origin main
echo "Published. GitHub Pages will redeploy within ~1 minute:"
echo "  https://milanpcooper-ui.github.io/world-cup-2026-bracket-model/"

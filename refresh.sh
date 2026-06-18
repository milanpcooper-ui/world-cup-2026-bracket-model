#!/usr/bin/env bash
# Deterministic auto-refresh: pull latest, fetch CROSS-VALIDATED results from real
# sports feeds, and publish. There is NO model/LLM in the results path — scores come
# only from authoritative feeds that agree with each other (fetch_results.py), so
# there is nothing to hallucinate. This is what the scheduled job runs.
#
# Usage:  bash refresh.sh ["commit summary"]
set -uo pipefail
cd "$(dirname "$0")"
SUMMARY="${1:-validated results refresh}"

echo "[refresh] $(date -u +%Y-%m-%dT%H:%MZ) — pulling latest…"
# --autostash keeps a stray local edit from blocking the rebase (and from wedging
# the unattended loop); origin/main is the source of truth.
if ! git pull --rebase --autostash origin main; then
  echo "[refresh] git pull failed — aborting."
  exit 1
fi

echo "[refresh] fetching validated results from feeds…"
python3 fetch_results.py
fetch_rc=$?
if [ "$fetch_rc" = "2" ]; then
  # WC26-RESULT-CONFLICT also appears in fetch_results.py output above; echo the
  # marker again here so a single grep of the run log catches it. Non-fatal:
  # conflicts are never ingested, so we still publish whatever was clean.
  echo "[refresh] WC26-RESULT-CONFLICT: feeds disagreed on a result (not ingested) — review."
elif [ "$fetch_rc" != "0" ]; then
  echo "[refresh] fetch_results.py errored (rc=$fetch_rc) — aborting before publish."
  exit "$fetch_rc"
fi

echo "[refresh] refreshing market odds (ESPN match 1X2 + Polymarket title)…"
# Odds are calibration inputs, not facts — a feed hiccup must NOT abort the run;
# fetch_odds.py only rewrites a file when the market moved materially, so this is a
# no-op on quiet runs and never spams commits.
python3 fetch_odds.py || echo "[refresh] NOTE: odds refresh had an issue (non-fatal) — keeping last-known odds."

echo "[refresh] publishing (rebuilds + pushes only if an input changed)…"
# publish.sh re-validates the inputs (incl. the kickoff-time gate) as a final
# backstop, then rebuilds and pushes only when results_log.json actually changed.
bash publish.sh "$SUMMARY"

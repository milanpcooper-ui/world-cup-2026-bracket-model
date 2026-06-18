# EXECUTE — World Cup 2026 model rebuild

Refresh the predictive bracket with the latest results **and** the latest betting odds,
then publish to the live site.

## Automated rebuilds

During the tournament a scheduled job runs **`refresh.sh`** every 3 hours. It is fully
deterministic — **no LLM decides results**:

```
git pull --rebase --autostash  →  python3 fetch_results.py  →  bash publish.sh
```

`fetch_results.py` reads finished group-stage scores from **real sports feeds and
cross-validates them** (see below), appending only confirmed results to `results_log.json`.
`publish.sh` then rebuilds and pushes to GitHub Pages **only when an input actually changed**
(fixed RNG seeds mean a no-data rebuild is a no-op, so it never spams commits). The Pages site
redeploys within ~1 minute. Because results come only from feeds that agree with each other —
never from a model's guess — fabricated scores are structurally impossible.

### How results are validated (`fetch_results.py`)
For every scheduled group game not already recorded, it queries independent sources and
ingests a score only when they agree and the game is genuinely final:
- **ESPN** (primary, no key) — authoritative status (`post`/`FT`/`completed`) + final score,
  matched by stable FIFA 3-letter team code.
- **TheSportsDB** (secondary, free) — cross-check.
- **football-data.org** (optional third) — enabled if `FOOTBALL_DATA_TOKEN` is set.

Policy: **CONFIRMED** (≥2 sources agree → ingest) · **SINGLE** (only the primary is final →
ingest, flagged; use `--require-two-sources` to require two) · **CONFLICT** (sources disagree
→ rejected + logged, never ingested; exit 2) · **PENDING** (not final / kickoff+2.5h not
elapsed → skip, caught next run). Every ingested score must also pass the deterministic
kickoff-time gate (`schedule_gate.py`). Run `python3 fetch_results.py --dry-run` to preview,
`--full` to scan the whole group stage (backfill).

## Updating it manually

From this repo folder:

1. `git pull --rebase` — start from latest.
2. **Results.** Run `python3 fetch_results.py` (or `bash refresh.sh` to fetch + publish in one
   step). It appends only feed-validated, genuinely-final group-stage scores — you do not, and
   should not, type scores in by hand. If you must hand-edit `results_log.json`, the same
   guardrails apply: a result is admissible only once its scheduled kickoff (`data.py`
   `GROUP_FIXTURES`, ET) + ~2.5h has passed, and only group-stage (same-group) games are
   ingested (knockouts are simulated). The kickoff-time gate (`schedule_gate.py`, enforced by
   `build.py` and `validate_inputs.py`) **rejects** a premature or cross-group score and
   `publish.sh` **aborts** (prints `WC26-PUBLISH-ABORTED` and reverts the edit). **Never
   invent or placeholder a score.**
3. **Odds (optional, manual).** Odds are no longer auto-refreshed. To update calibration, edit
   `odds.json` (top ~15 title-odds implied probabilities) and/or `match_odds.json` (1X2 lines
   for upcoming group games), exact `data.py` names. Leave unchanged if nothing moved.
4. **Publish:** `bash publish.sh "what changed"` — validates inputs, rebuilds, and pushes to
   GitHub Pages only if an input changed. The build prints a "WHAT CHANGED SINCE LAST BUILD"
   section.

See `CONTRIBUTING.md` for the exact input formats.

## Inputs & change tracking
- `results_log.json` — array of finished **group-stage** matches `{"h","a","hg","ag"}`. New finals get appended (deduped against `data.py`). A deterministic kickoff-time gate (`schedule_gate.py`) rejects any entry whose game can't have finished yet (kickoff + ~2.5h not elapsed) and any cross-group/knockout pairing; `build.py` skips such entries and `validate_inputs.py` errors on them, so a fabricated or premature score can never reach the build or the live site.
- `odds.json` — flat `{"Team": probability}` of current title odds; the model re-calibrates to it.
- `match_odds.json` — per-game 1X2 lines `[{"h","a","home","draw","away"}]` (implied probabilities; a `_src` note is allowed and ignored). Any scheduled, unplayed group game listed here is priced **directly off the market** (the model solves the Poisson scoring rates that reproduce the line) instead of the Elo gap. Played games and unknown teams are ignored automatically.
- `build.py` merges all three inputs, refits title odds to the market, runs 40,000 simulations, writes `results.json` (including a `match_calibration` block and a `changes` diff).
- `gen_dashboard.py` writes `index.html` + `World_Cup_2026_Predictor.html` + `version.json` from one template (light/dark toggle, team flags, a "⭐ Your team" route view for any of the 48 sides, mobile-first round-by-round bracket). A "Today's movement" card — a build-level context line, then each changed bracket box with a plain-English **why** it moved and chips for the results/odds that drove it — sits atop the Bracket tab; the Method tab shows both calibration checks. It bakes the GitHub Pages URL as the default `WC_SITE_URL` for absolute Open Graph tags (override the env var to host elsewhere).
- Change tracking: each run snapshots the prior output to `results_prev.json`, diffs it, and reports what moved (printed to console + `changes` block in `results.json` + dashboard banner). This includes **bracket matchup changes** — for every knockout box it compares the displayed `Team A vs Team B` pairing to the previous build and lists only the boxes whose pairing actually flipped (an odds shift that leaves the pairing unchanged is deliberately *not* reported), each annotated with the old/new matchup probability so you can tell a settled flip from a near-tie. Fixed sim seeds mean unchanged inputs reproduce identical numbers, so every reported change is real movement — not Monte Carlo noise. Threshold for probability moves is 2 points; matchup flips are reported regardless of margin.
- **Why attribution** (per flip): each matchup change carries a generated `why` sentence plus a structured `drivers` list. It traces the box back to the groups whose teams can reach it (a winner/runner-up slot, or a best-third pool), then names the input(s) that moved those groups this build — a newly-ingested result, a title-odds swing on a team entering/leaving the box, or a re-priced game line — and flags whether the new pairing is a settled call or a near-tie. A build-level `changes.summary` says what the rebuild ingested and whether the new score(s) or the odds refresh did most of the work. Because fixed seeds make every output move traceable to a changed input (results / title odds / per-game lines), this attribution is read straight off the input diff, not guessed.

## Files
- `data.py` `model.py` `annexC.txt` `build.py` `gen_dashboard.py` — the model (don't edit unless you know why).
- `fetch_results.py` — pulls finished group-stage results from real sports feeds and
  cross-validates them; appends confirmed scores to `results_log.json` (no LLM, no guessing).
- `schedule_gate.py` — deterministic kickoff-time gate shared by `fetch_results.py`,
  `build.py`, and `validate_inputs.py`.
- `refresh.sh` — the deterministic auto-refresh: `git pull` → `fetch_results.py` → `publish.sh`.
- `publish.sh` — validate inputs, rebuild, push to GitHub Pages, only when an input changed.
- `results_log.json` `odds.json` `match_odds.json` — the three live inputs (`results_log.json`
  is now feed-populated; the two odds files are manual).
- `results.json` — latest computed output (includes a `changes` block vs the prior build).
- `results_prev.json` — auto-saved snapshot of the previous build, for the diff (gitignored).
- `index.html` / `World_Cup_2026_Predictor.html` — the dashboard (Pages root + standalone copy); `version.json` powers the "newer build available" banner.

## Re-run with no new data
To rebuild from the current inputs (e.g. after a code change):
`python3 build.py && python3 gen_dashboard.py`. Note `publish.sh` would no-op here (no
input changed), so commit and push manually if you actually want to redeploy.

## Note
Early in the group stage the model leans on pre-tournament odds; it sharpens as real
results land (group stage runs Jun 11–27, knockouts Jun 28–Jul 19, 2026).

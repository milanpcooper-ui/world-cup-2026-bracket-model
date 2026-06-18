# EXECUTE — World Cup 2026 model rebuild

Refresh the predictive bracket with the latest results **and** the latest betting odds,
then publish to the live site.

## Automated rebuilds

During the tournament a scheduled job on the maintainer's machine runs this workflow
every 3 hours: it pulls the latest finished results and refreshed odds into the JSON
inputs, then calls `publish.sh`, which rebuilds and pushes to GitHub Pages **only when an
input actually changed** (fixed RNG seeds mean a no-data rebuild is a no-op, so it never
spams commits). The Pages site redeploys within ~1 minute.

## Updating it manually

From this repo folder:

1. `git pull --rebase` — start from latest.
2. **Results.** Find every **group-stage** World Cup match that has finished with a final
   score and isn't already in `results_log.json` / `data.py`. Cross-check each score against
   a second source (ESPN, CBS Sports, Fox Sports, FIFA). Append each as `{"h","a","hg","ag"}`
   using the EXACT team names in `data.py` (e.g. "Türkiye", "South Korea", "Côte d'Ivoire",
   "DR Congo", "Bosnia & Herzegovina", "Curaçao"). Never duplicate one already recorded.

   **Hard rule — only enter a game that has actually been played.** A result is admissible
   only once its scheduled kickoff (`data.py` `GROUP_FIXTURES`, ET) plus ~2.5h has passed in
   real time. This is enforced deterministically by a kickoff-time gate (`schedule_gate.py`,
   used by both `build.py` and `validate_inputs.py`); a premature score is **rejected**, and
   `publish.sh` **aborts** rather than ship it. The model ingests group-stage results only —
   knockout rounds are simulated, so a cross-group ("knockout") result is rejected too. If a
   publish aborts on a rejected result (look for `WC26-PUBLISH-ABORTED`), `publish.sh` reverts
   the input edits so the next run starts clean; if you edited inputs by hand, run
   `git checkout -- results_log.json` to clear the rejected entry. **Never invent, guess, or
   placeholder a score** — if a game isn't finished or sources disagree, skip it.
3. **Odds (optional).** Refresh `odds.json` (top ~15 title-odds implied probabilities) and
   `match_odds.json` (1X2 lines for upcoming group games), exact `data.py` names. Leave
   unchanged if nothing moved.
4. **Publish:** `bash publish.sh "what changed"` — rebuilds and pushes to GitHub Pages only
   if an input changed. The build prints a "WHAT CHANGED SINCE LAST BUILD" section.

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
- `publish.sh` — rebuild + push to GitHub Pages, only when an input changed.
- `results_log.json` `odds.json` `match_odds.json` — the three live inputs.
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

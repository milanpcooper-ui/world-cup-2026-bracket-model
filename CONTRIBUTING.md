# Contributing

Thanks for helping improve the World Cup 2026 predictive bracket! It's a small,
data-driven model. Live results are refreshed automatically every 3 hours from
cross-validated sports feeds (`fetch_results.py`; odds are updated manually), so the most
useful PRs tend to be **model & calibration improvements, more reliable/additional data
sources, and UX/accessibility fixes** — though data corrections are always welcome. Many
changes need no code beyond a JSON edit.

## The three live inputs (no code needed)

`build.py` reads three JSON files each rebuild. Use the exact team names from `data.py`.

- **`results_log.json`** — finished **group-stage** match scores, one object each:
  `{"h": "England", "a": "Croatia", "hg": 2, "ag": 1}`. Normally populated automatically by
  `fetch_results.py` from cross-validated feeds — you rarely edit it by hand. A kickoff-time
  gate (`schedule_gate.py`) rejects any score for a game that can't have finished yet (its
  scheduled kickoff + ~2.5h hasn't passed) and any cross-group/knockout pairing (the model
  simulates the knockouts; it doesn't ingest their results). If a legitimately-final score is
  rejected, check the kickoff in `data.py` `GROUP_FIXTURES` and your clock.
- **`odds.json`** — current title odds as implied probabilities, top ~15:
  `{"France": 0.17, "Spain": 0.17, ...}`. The model re-calibrates the rating spread to these.
- **`match_odds.json`** — per-game 1X2 lines for upcoming, unplayed group games:
  `[{"h": "...", "a": "...", "home": 0.55, "draw": 0.25, "away": 0.20}]` (implied,
  de-vigged by the model). Played games and unknown teams are ignored automatically.

Before opening a data PR, run `python3 validate_inputs.py` to catch bad JSON, mistyped
team names (e.g. `Turkey` vs `Türkiye`), and results for games that haven't finished yet
(the kickoff-time gate). CI runs the same check automatically on PRs that touch these
files — it parses the JSON and reads `data.py` statically, never running the model.

`EXECUTE.md` documents the full workflow.

## Rebuild locally

```sh
python3 build.py && python3 gen_dashboard.py
# then open World_Cup_2026_Predictor.html  (index.html is the same dashboard)
```

Requires Python 3 and NumPy (`pip install numpy`). `build.py` runs ~40k simulations
(a few seconds) and writes `results.json`; `gen_dashboard.py` renders the dashboard.

## Good first contributions

- Sharpen the model: calibration, the knockout extra-time/penalty model, tie-breaks (`model.py`).
- More reliable or automated data sourcing for results and odds.
- Accessibility and dashboard polish (`gen_dashboard.py`).
- Replace `APPROX` Elo values in `data.py` with sourced numbers — a nice data-quality
  cleanup, though the top of the bracket is market-anchored so these mostly nudge
  lower-tier sides.

## How it works

- `model.py` — the simulation engine + market calibration.
- `data.py` — static tournament data (groups, Elo, fixtures, venues, knockout slots).
- `annexC.txt` — FIFA Annex C third-place allocation table (495 rows).
- `gen_dashboard.py` — renders `results.json` into the standalone HTML dashboard.
- `fetch_results.py` — fetches finished results from real feeds (ESPN + TheSportsDB +
  optional football-data.org), cross-validates them, and appends to `results_log.json`.
- `schedule_gate.py` — the deterministic kickoff-time gate (shared safety net).
- `refresh.sh` — the deterministic auto-refresh (`git pull` → `fetch_results.py` → `publish.sh`).

See the README and the dashboard's **Method** tab for the modelling assumptions.

## Conventions

- **Fixed RNG seeds**: unchanged inputs reproduce identical numbers, so any diff in
  `results.json` is real movement, not Monte Carlo noise. Keep it that way — don't
  introduce unseeded randomness.
- Don't commit `results_prev.json` (gitignored; it's the day-over-day diff snapshot).
- Keep `data.py` team names canonical — every input file keys off them.

## Data & disclaimer

Inputs are publicly reported facts (schedules, venues, Elo ratings, market odds) used
for a non-commercial forecast. This project is **not affiliated with FIFA** and is
**not betting advice**. By contributing you agree your contributions are licensed under
the repository's [MIT License](LICENSE).

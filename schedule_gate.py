"""Deterministic kickoff-time gate — refuse to ingest a match result before the
match could physically have finished.

This is the structural defense against an updater (human or automated) recording a
score for a game that has not been played yet. Two rules:

  1. Group-stage results only. The model (model.build_group_matches) fixes
     intra-group scores; the knockout bracket is always fully simulated and never
     fed actual results. So a cross-group ("knockout") result has no legitimate
     effect on the model — it can only mislead — and is rejected outright. This
     also means there is no weak "earliest knockout" floor for a fabricated
     late-round score to slip past.
  2. Kickoff has passed. For a group game, data.py `GROUP_FIXTURES` carries its
     date + ET kickoff, so we compute the earliest real-world instant by which it
     could have a final score and compare to the actual current time. A result
     whose game has not finished is rejected — no matter how plausible its
     scoreline looks.

Knockout results are handled by a SEPARATE, equally-strict path: they enter via
ko_results.json keyed by match number (not a team pair), and ko_result_admissible()
gates each on that specific knockout match's scheduled kickoff. This is why
result_admissible() above can keep rejecting every cross-group pair outright — the
group boundary is never relaxed; knockout ingestion is an independent gate.

Pure Python, no project imports, so this is safe to import from validate_inputs.py
(which must never execute data.py). Callers supply the schedule structures however
they obtain them: build.py from `import data`, validate_inputs.py from its static
ast read of data.py.
"""
import datetime

# The whole tournament (group + knockout) falls in this calendar year.
SEASON_YEAR = 2026

# A match is not treated as final until kickoff + this much wall-clock time has
# elapsed. 90' + halftime + stoppage is ~1h55; knockouts can add extra time and
# penalties. 2.5h clears a group game comfortably. Erring long is safe: it can
# only delay a genuinely-finished result by at most one rebuild cycle — it can
# never let an unplayed game's (fabricated) score slip through.
MATCH_COMPLETION_BUFFER = datetime.timedelta(hours=2, minutes=30)

_MONTHS = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
           "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}

# The tournament window (Jun–Jul) is entirely within US Eastern Daylight Time
# (UTC-4); no DST transition occurs in it, so a fixed offset is exact for every
# fixture. All schedule times in data.py are stated in ET.
_ET = datetime.timezone(datetime.timedelta(hours=-4))


def parse_kickoff_utc(date_str, time_str, year=SEASON_YEAR):
    """('Jun 18', '12:00 PM') -> timezone-aware UTC datetime of kickoff.

    The schedule lists late West-coast games as e.g. 'Jun 16' '12:00 AM' — that
    slot actually runs at 00:00 ET on the *following* day (after that date's 9pm
    game). Any post-midnight slot (hour < 6) is rolled forward one day. Rolling
    toward a *later* kickoff is the safe direction: it can only delay a real
    result, never admit an unplayed one.
    """
    mon, day = date_str.split()
    month, day = _MONTHS[mon], int(day)
    hhmm, ampm = time_str.strip().upper().split()
    hh, mm = (int(x) for x in hhmm.split(":"))
    if ampm == "AM":
        hh = 0 if hh == 12 else hh
    else:  # PM
        hh = 12 if hh == 12 else hh + 12
    dt = datetime.datetime(year, month, day, hh, mm, tzinfo=_ET)
    if hh < 6:  # post-midnight slot listed under the prior evening's date
        dt += datetime.timedelta(days=1)
    return dt.astimezone(datetime.timezone.utc)


def group_fixture_kickoffs(group_fixtures, year=SEASON_YEAR):
    """{frozenset({home, away}): kickoff_utc} for every scheduled group game.

    Rows are (home, away, group, 'Mon DD', 'h:mm ap', city); only the first five
    fields are read. A row that fails to parse is skipped (the caller still has
    other validators for malformed schedule data)."""
    out = {}
    for row in group_fixtures:
        try:
            h, a, _grp, date_str, time_str = row[0], row[1], row[2], row[3], row[4]
            out[frozenset((h, a))] = parse_kickoff_utc(date_str, time_str, year)
        except Exception:
            continue
    return out


def knockout_kickoffs(ko_info, year=SEASON_YEAR):
    """{match_no: kickoff_utc} for every knockout match.

    KO_INFO maps match_no -> (city, date_str, time_str) — note the field order
    differs from GROUP_FIXTURES (here date/time are positions 1 and 2). A row that
    fails to parse is skipped. Pure-Python like group_fixture_kickoffs, so
    validate_inputs.py can build this from a static read of data.py."""
    out = {}
    for mno, row in (ko_info or {}).items():
        try:
            date_str, time_str = row[1], row[2]
            out[int(mno)] = parse_kickoff_utc(date_str, time_str, year)
        except Exception:
            continue
    return out


def ko_result_admissible(match_no, ko_kickoffs, now_utc,
                         buffer=MATCH_COMPLETION_BUFFER):
    """Whether a KNOCKOUT result for `match_no` may be ingested as of `now_utc`.

    Returns (ok: bool, reason: str|None). This is the knockout analog of
    result_admissible(): a knockout result is admitted only once its scheduled
    kickoff + completion buffer has passed, so a premature/fabricated late-round
    score cannot slip through. Knockout results enter through a SEPARATE input
    (ko_results.json) keyed by match number, so this gate deliberately leaves
    result_admissible()'s group-stage cross-group rejection untouched — the two
    paths stay independent and equally strict."""
    ko = ko_kickoffs.get(int(match_no))
    if ko is None:
        return False, (f"match {match_no} has no scheduled kickoff in KO_INFO — "
                       f"not a knockout fixture this model ingests")
    ready = ko + buffer
    if now_utc < ready:
        return False, (
            f"knockout match {match_no} kicks off {ko:%b %d %H:%MZ}; not final "
            f"until ~{ready:%b %d %H:%MZ} (now {now_utc:%b %d %H:%MZ}) — game "
            f"hasn't been played yet, result not ingestible")
    return True, None


def result_admissible(h, a, group_of, group_kickoffs, now_utc,
                      buffer=MATCH_COMPLETION_BUFFER):
    """Decide whether a result for (h, a) may be ingested as of `now_utc`.

    Returns (ok: bool, reason: str|None). ok=False means the result must not be
    recorded — either it isn't a game this model ingests, or its game can't have
    finished yet, so the score is a placeholder/fabrication.

      - cross-group pair -> a knockout pairing. The model ingests group-stage
        results only (the knockout bracket is simulated, never fed results), so a
        cross-group result has no legitimate effect — reject it. This also closes
        any "earliest knockout floor" a fabricated late-round score could slip past.
      - same-group pair  -> gate on that specific group game's scheduled kickoff:
        admit only once kickoff + buffer has passed.
      - unknown team / no schedule entry -> admit. We have no kickoff to gate on;
        unknown-team handling belongs to the other validators.
    """
    gh, ga = group_of.get(h), group_of.get(a)

    # One or both teams unknown to the schedule: not this gate's job.
    if gh is None or ga is None:
        return True, None

    # Different groups -> a knockout pairing this model does not ingest.
    if gh != ga:
        return False, (
            f"{h} vs {a} is a cross-group (knockout) pairing; this model records "
            f"group-stage results only — knockout rounds are simulated, not fed "
            f"actual results, so this entry has no legitimate effect and is rejected")

    # Same group -> a specific scheduled group fixture; gate on its kickoff.
    ko = group_kickoffs.get(frozenset((h, a)))
    if ko is None:
        return True, None  # same group but no schedule row found; don't block
    ready = ko + buffer
    if now_utc < ready:
        return False, (
            f"{h} vs {a} kicks off {ko:%b %d %H:%MZ}; not final until "
            f"~{ready:%b %d %H:%MZ} (now {now_utc:%b %d %H:%MZ}) — game "
            f"hasn't been played yet, result not ingestible")
    return True, None

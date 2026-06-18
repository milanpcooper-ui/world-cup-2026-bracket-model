#!/usr/bin/env python3
"""Fetch finished group-stage results from real data feeds, cross-validate across
multiple independent sources, and append only confirmed scores to results_log.json.

This replaces the old "ask a headless LLM what finished" step — which had no ground
truth and fabricated scores (and fake citations) for games that hadn't kicked off.
Here, results come ONLY from authoritative sports feeds, and a score is recorded
only when the sources agree and the game is genuinely final. No model judgement is
involved, so there is nothing to hallucinate.

Sources (no paid key required):
  - ESPN site API  (primary)   — structured status (pre/in/post + FT/completed),
                                 final scores, stable FIFA 3-letter team codes.
  - TheSportsDB    (secondary) — free "FIFA World Cup" league feed, FT status,
                                 scores. Used to cross-check ESPN.
  - football-data.org (optional tertiary) — enabled only if FOOTBALL_DATA_TOKEN is
                                 set in the environment (free tier). Adds a third
                                 independent vote.

Ingestion policy (per scheduled group fixture not already recorded):
  - CONFIRMED  : >=2 sources report it FINAL and the scores agree  -> ingest.
  - SINGLE     : exactly one source (must include the primary) reports it FINAL,
                 others silent/unavailable                          -> ingest, flagged
                 (a feed lagging shouldn't stall a real result; the primary is
                 authoritative and the kickoff-time gate still backstops it).
  - CONFLICT   : sources disagree on the score                      -> DO NOT ingest,
                 log loudly for human review.
  - PENDING    : not final yet / kickoff+buffer not elapsed         -> skip (next run).

Every ingested result must additionally pass the deterministic kickoff-time gate
(schedule_gate) — belt-and-suspenders so fetch_results and validate_inputs.py never
disagree about whether a game could have finished.

Usage:
    python3 fetch_results.py            # fetch recent window, append to results_log.json
    python3 fetch_results.py --dry-run  # report only; write nothing
    python3 fetch_results.py --full     # scan the whole group stage (backfill/first run)
    python3 fetch_results.py --require-two-sources   # treat SINGLE as PENDING
Exit code 0 on success (including "nothing new"); 2 if a source CONFLICT was found
(so the caller can alert) — note conflicts are still never ingested.
"""
import os, sys, json, time, datetime, urllib.request, urllib.error, unicodedata

import data as D
import schedule_gate as SG

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_LOG = os.path.join(HERE, "results_log.json")

# ESPN FIFA 3-letter code -> data.py canonical team name. Validated against
# D.TEAM_GROUP at startup, so a typo or a team the feed renames fails loudly
# rather than silently dropping a game.
FIFA_TO_CANON = {
    "ALG": "Algeria", "ARG": "Argentina", "AUS": "Australia", "AUT": "Austria",
    "BEL": "Belgium", "BIH": "Bosnia & Herzegovina", "BRA": "Brazil", "CAN": "Canada",
    "CIV": "Côte d'Ivoire", "COD": "DR Congo", "COL": "Colombia", "CPV": "Cape Verde",
    "CRO": "Croatia", "CUW": "Curaçao", "CZE": "Czechia", "ECU": "Ecuador",
    "EGY": "Egypt", "ENG": "England", "ESP": "Spain", "FRA": "France",
    "GER": "Germany", "GHA": "Ghana", "HAI": "Haiti", "IRN": "Iran",
    "IRQ": "Iraq", "JOR": "Jordan", "JPN": "Japan", "KOR": "South Korea",
    "KSA": "Saudi Arabia", "MAR": "Morocco", "MEX": "Mexico", "NED": "Netherlands",
    "NOR": "Norway", "NZL": "New Zealand", "PAN": "Panama", "PAR": "Paraguay",
    "POR": "Portugal", "QAT": "Qatar", "RSA": "South Africa", "SCO": "Scotland",
    "SEN": "Senegal", "SUI": "Switzerland", "SWE": "Sweden", "TUN": "Tunisia",
    "TUR": "Türkiye", "URU": "Uruguay", "USA": "USA", "UZB": "Uzbekistan",
}

# Alias table for name-based feeds (TheSportsDB, football-data.org). Keys are the
# accent/case/punctuation-normalized variant; values are canonical names. The
# normalizer below also matches any canonical name directly, so only true aliases
# need listing here.
NAME_ALIASES = {
    "ivory coast": "Côte d'Ivoire", "cote divoire": "Côte d'Ivoire",
    "congo dr": "DR Congo", "dr congo": "DR Congo",
    "democratic republic of congo": "DR Congo", "congo democratic republic": "DR Congo",
    "turkey": "Türkiye", "turkiye": "Türkiye",
    "united states": "USA", "united states of america": "USA", "usa": "USA",
    "south korea": "South Korea", "korea republic": "South Korea",
    "republic of korea": "South Korea",
    "bosnia and herzegovina": "Bosnia & Herzegovina",
    "bosnia herzegovina": "Bosnia & Herzegovina", "bosnia": "Bosnia & Herzegovina",
    "cape verde": "Cape Verde", "cape verde islands": "Cape Verde",
    "czech republic": "Czechia", "czechia": "Czechia",
    "curacao": "Curaçao",
}


def _norm(s):
    """lowercase, strip accents, turn every non-alphanumeric (hyphen, '&', '.', …)
    into a space and collapse runs — so "Bosnia-Herzegovina", "Bosnia & Herzegovina"
    and "Bosnia and Herzegovina" all normalize identically for tolerant matching."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = "".join(c if c.isalnum() else " " for c in s.lower())
    return " ".join(s.split())


_CANON_BY_NORM = {_norm(t): t for t in D.TEAM_GROUP}
_ALIAS_BY_NORM = {_norm(k): v for k, v in NAME_ALIASES.items()}


def canon_from_name(name):
    """Map a free-text team name from a feed to a data.py canonical name, or None."""
    n = _norm(name)
    if n in _CANON_BY_NORM:
        return _CANON_BY_NORM[n]
    if n in _ALIAS_BY_NORM:
        return _ALIAS_BY_NORM[n]
    return None


def _validate_team_map():
    """Fail fast if FIFA_TO_CANON is wrong or incomplete vs data.py."""
    bad = [c for c in FIFA_TO_CANON.values() if c not in D.TEAM_GROUP]
    if bad:
        sys.exit(f"FETCH ERROR: FIFA_TO_CANON has names not in data.py: {bad}")
    missing = set(D.TEAM_GROUP) - set(FIFA_TO_CANON.values())
    if missing:
        sys.exit(f"FETCH ERROR: FIFA_TO_CANON is missing teams: {sorted(missing)}")


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def _get_json(url, headers=None, timeout=20, retries=2):
    """GET url -> parsed JSON, or None on any failure (after retries). Never raises;
    a down source must degrade to 'unavailable', not crash the run."""
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers or {"User-Agent": "wc26-bracket/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001 — intentional: any failure -> unavailable
            last = e
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    print(f"  source fetch failed ({url.split('?')[0]}): {last}")
    return None


GROUP_START = datetime.date(2026, 6, 11)
GROUP_END = datetime.date(2026, 6, 27)
WINDOW_DAYS = 4  # rolling look-back for steady-state runs

# Set by main(): when True, scan the whole group stage (backfill / first run);
# otherwise just a recent window, which keeps request counts low (free feeds
# rate-limit) while still re-checking every recently-finished game each run.
FULL_SCAN = False


def _tournament_dates():
    """YYYYMMDD ET date strings to query. A rolling window [today-WINDOW_DAYS,
    today+1] by default (recent finals re-checked every run; anything missed is
    caught next run), or the full Jun 11–27 group stage when FULL_SCAN is set."""
    now = datetime.datetime.now(datetime.timezone.utc)
    if FULL_SCAN:
        lo, hi = GROUP_START, GROUP_END
    else:
        # "today" in US Eastern (the schedule's reference clock).
        today_et = (now - datetime.timedelta(hours=4)).date()
        lo = max(GROUP_START, today_et - datetime.timedelta(days=WINDOW_DAYS))
        hi = min(GROUP_END, today_et + datetime.timedelta(days=1))
    out, d = set(), lo
    while d <= hi:
        out.add(d.strftime("%Y%m%d"))
        d += datetime.timedelta(days=1)
    if not FULL_SCAN:
        out |= _stranded_dates(now)  # re-query any past game missed beyond the window
    return sorted(out)


# ---------------------------------------------------------------------------
# SOURCES — each returns {frozenset({canon_h, canon_a}): {"h","a","hg","ag","final"}}
# keyed/oriented to whatever the source reports; reorientation to the fixture
# happens in reconcile().
# ---------------------------------------------------------------------------
def fetch_espn():
    out, name = {}, "ESPN"
    for d in _tournament_dates():
        data = _get_json(
            f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates={d}")
        if data is None:
            return None, name  # primary unreachable -> signal unavailable
        for ev in data.get("events", []):
            comp = (ev.get("competitions") or [{}])[0]
            st = (ev.get("status") or {}).get("type") or {}
            # "final" only for a genuinely-completed match: ESPN's authoritative
            # `completed` flag AND state "post", excluding abandoned/postponed/
            # canceled/suspended terminal states (which can also report state=post).
            name = (st.get("name") or "").upper()
            blocked = any(k in name for k in ("ABANDON", "POSTPON", "CANCEL", "SUSPEND", "FORFEIT"))
            final = bool(st.get("completed")) and st.get("state") == "post" and not blocked
            teams = {}
            for c in comp.get("competitors", []):
                code = (c.get("team") or {}).get("abbreviation")
                canon = FIFA_TO_CANON.get(code)
                try:
                    goals = int(c.get("score"))
                except (TypeError, ValueError):
                    goals = None
                teams[c.get("homeAway")] = (canon, goals)
            h, a = teams.get("home"), teams.get("away")
            if not h or not a or h[0] is None or a[0] is None:
                continue
            if final and (h[1] is None or a[1] is None):
                continue
            out[frozenset((h[0], a[0]))] = {
                "h": h[0], "a": a[0], "hg": h[1], "ag": a[1], "final": final}
    return out, name


def fetch_thesportsdb():
    out, name = {}, "TheSportsDB"
    dates = _tournament_dates()
    got_any = False
    for i, d in enumerate(dates):
        if i:
            time.sleep(0.5)  # gentle: free tier rate-limits bursts
        iso = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        data = _get_json(
            f"https://www.thesportsdb.com/api/v1/json/3/eventsday.php?d={iso}&s=Soccer")
        if data is None:
            # one date failing (e.g. transient 429) shouldn't void the whole
            # source; skip it and keep whatever other dates returned.
            continue
        got_any = True
        for ev in (data.get("events") or []):
            if "World Cup" not in (ev.get("strLeague") or ""):
                continue
            if (ev.get("strPostponed") or "no").lower() == "yes":
                continue
            ch = canon_from_name(ev.get("strHomeTeam"))
            ca = canon_from_name(ev.get("strAwayTeam"))
            if not ch or not ca:
                continue
            try:
                hg, ag = int(ev.get("intHomeScore")), int(ev.get("intAwayScore"))
            except (TypeError, ValueError):
                hg = ag = None
            final = (ev.get("strStatus") or "").upper() in ("FT", "AET", "PEN", "FINISHED")
            if final and (hg is None or ag is None):
                continue
            out[frozenset((ch, ca))] = {"h": ch, "a": ca, "hg": hg, "ag": ag, "final": final}
    if not got_any:
        return None, name  # every date failed -> source unavailable this run
    return out, name


def fetch_football_data():
    """Optional third source — only if FOOTBALL_DATA_TOKEN is set (free tier)."""
    token = os.environ.get("FOOTBALL_DATA_TOKEN")
    name = "football-data.org"
    if not token:
        return "disabled", name
    data = _get_json("https://api.football-data.org/v4/competitions/WC/matches",
                     headers={"X-Auth-Token": token})
    if data is None:
        return None, name
    out = {}
    for m in data.get("matches", []):
        ch = canon_from_name((m.get("homeTeam") or {}).get("name"))
        ca = canon_from_name((m.get("awayTeam") or {}).get("name"))
        if not ch or not ca:
            continue
        ft = (m.get("score") or {}).get("fullTime") or {}
        hg, ag = ft.get("home"), ft.get("away")
        final = m.get("status") == "FINISHED"
        if final and (hg is None or ag is None):
            continue
        out[frozenset((ch, ca))] = {"h": ch, "a": ca,
                                    "hg": int(hg) if hg is not None else None,
                                    "ag": int(ag) if ag is not None else None, "final": final}
    return out, name


SOURCES = [fetch_espn, fetch_thesportsdb, fetch_football_data]
PRIMARY = "ESPN"


# ---------------------------------------------------------------------------
def _recorded_scores():
    """{frozenset({h,a}): (h, a, hg, ag)} for every result already recorded in
    data.py RESULTS or results_log.json (in its stored orientation)."""
    rec = {frozenset((h, a)): (h, a, hg, ag) for (h, a, hg, ag) in D.RESULTS}
    if os.path.exists(RESULTS_LOG):
        try:
            for e in json.load(open(RESULTS_LOG)):
                rec[frozenset((e["h"], e["a"]))] = (e["h"], e["a"], int(e["hg"]), int(e["ag"]))
        except Exception:
            pass
    return rec


def _recorded_pairs():
    """frozensets already recorded in data.py RESULTS or results_log.json."""
    return set(_recorded_scores())


def _group_fixtures():
    """{frozenset({home,away}): (home, away)} for every scheduled group game,
    in the schedule's home/away orientation."""
    fx = {}
    for row in D.GROUP_FIXTURES:
        h, a = row[0], row[1]
        fx[frozenset((h, a))] = (h, a)
    return fx


def _label_date(date_str):
    """'Jun 18' -> datetime.date(2026, 6, 18) (the ET matchday label)."""
    mon, day = date_str.split()
    return datetime.date(SG.SEASON_YEAR, SG._MONTHS[mon], int(day))


def _stranded_dates(now):
    """ET matchday dates (YYYYMMDD) of past-due, still-unrecorded group fixtures
    that fall OUTSIDE the default rolling window. Without this, a game missed for
    more than WINDOW_DAYS (e.g. a multi-day outage of both free feeds) would drop
    out of the query window and never be re-fetched. Adding just those specific
    dates self-heals stranding while keeping normal request counts low."""
    have = _recorded_pairs()
    kos = SG.group_fixture_kickoffs(D.GROUP_FIXTURES)
    today_et = (now - datetime.timedelta(hours=4)).date()
    window_lo = max(GROUP_START, today_et - datetime.timedelta(days=WINDOW_DAYS))
    out = set()
    for row in D.GROUP_FIXTURES:
        key = frozenset((row[0], row[1]))
        ko = kos.get(key)
        if key in have or ko is None:
            continue
        if ko + SG.MATCH_COMPLETION_BUFFER >= now:
            continue  # not past-due yet (still legitimately pending)
        md = _label_date(row[3])
        if md < window_lo:  # older than the rolling window -> would be stranded
            out.add(md.strftime("%Y%m%d"))
    return out


def reconcile(require_two_sources=False):
    """Pull every source, then decide each unrecorded group fixture. Returns
    (to_ingest, conflicts, pending, source_status)."""
    now = datetime.datetime.now(datetime.timezone.utc)
    group_kos = SG.group_fixture_kickoffs(D.GROUP_FIXTURES)
    recorded = _recorded_scores()
    fixtures = _group_fixtures()

    source_data, source_status = {}, {}
    for fn in SOURCES:
        res, sname = fn()
        if res == "disabled":
            source_status[sname] = "disabled"
        elif res is None:
            source_status[sname] = "unavailable"
        else:
            source_status[sname] = f"ok ({sum(1 for v in res.values() if v['final'])} final)"
            source_data[sname] = res

    to_ingest, conflicts, pending = [], [], []

    for key, (fh, fa) in fixtures.items():
        # collect each source's FINAL verdict for this fixture, oriented to (fh, fa)
        votes = {}  # source -> (hg, ag) in fixture orientation
        for sname, res in source_data.items():
            g = res.get(key)
            if not g or not g["final"]:
                continue
            votes[sname] = (g["hg"], g["ag"]) if g["h"] == fh else (g["ag"], g["hg"])

        # ---- already recorded: never overwrite, but flag a confirmed contradiction ----
        if key in recorded:
            rh, ra, rhg, rag = recorded[key]
            rec_score = (rhg, rag) if rh == fh else (rag, rhg)  # orient to (fh, fa)
            distinct = set(votes.values())
            # only escalate if >=2 sources AGREE on a score that differs from the log
            if len(votes) >= 2 and len(distinct) == 1 and distinct != {rec_score}:
                conflicts.append({"h": fh, "a": fa, "recorded": rec_score,
                                  "sources_say": votes, "kind": "recorded_mismatch"})
            continue

        if not votes:
            pending.append((fh, fa))
            continue

        distinct = set(votes.values())
        if len(distinct) > 1:
            conflicts.append({"h": fh, "a": fa, "votes": dict(votes), "kind": "source_disagree"})
            continue

        (hg, ag) = distinct.pop()
        confirmed = len(votes) >= 2
        has_primary = PRIMARY in votes
        if not confirmed:
            # single-source result: ingest only if it's the authoritative primary
            # and two sources aren't being required.
            if require_two_sources or not has_primary:
                pending.append((fh, fa))
                continue

        # deterministic kickoff-time gate — must also be satisfied, so this never
        # writes something validate_inputs.py would then reject.
        ok, reason = SG.result_admissible(fh, fa, D.TEAM_GROUP, group_kos, now)
        if not ok:
            pending.append((fh, fa))
            continue

        to_ingest.append({"h": fh, "a": fa, "hg": hg, "ag": ag,
                          "sources": sorted(votes), "confirmed": confirmed})

    return to_ingest, conflicts, pending, source_status


def append_results(to_ingest):
    """Append confirmed results to results_log.json (deduped), preserving order."""
    log = []
    if os.path.exists(RESULTS_LOG):
        try:
            log = json.load(open(RESULTS_LOG))
        except Exception:
            log = []
    have = {frozenset((e["h"], e["a"])) for e in log}
    added = 0
    for r in to_ingest:
        key = frozenset((r["h"], r["a"]))
        if key in have:
            continue
        log.append({"h": r["h"], "a": r["a"], "hg": int(r["hg"]), "ag": int(r["ag"])})
        have.add(key)
        added += 1
    if added:
        with open(RESULTS_LOG, "w") as f:
            json.dump(log, f, indent=2)
            f.write("\n")
    return added


def main(argv):
    global FULL_SCAN
    dry = "--dry-run" in argv
    require_two = "--require-two-sources" in argv
    FULL_SCAN = "--full" in argv
    _validate_team_map()

    print("Fetching results from sources…")
    to_ingest, conflicts, pending, status = reconcile(require_two_sources=require_two)

    n_ok = sum(1 for st in status.values() if st.startswith("ok"))
    print("\nSource status:")
    for s, st in status.items():
        print(f"  {s:18s} {st}")

    if conflicts:
        # WC26-RESULT-CONFLICT is a stable, greppable marker (mirrors publish.sh's
        # WC26-PUBLISH-ABORTED) so an unattended run's log can be alerted on.
        print(f"\n⚠️  WC26-RESULT-CONFLICT — {len(conflicts)} conflict(s), NOT ingested, review:")
        for c in conflicts:
            if c.get("kind") == "recorded_mismatch":
                print(f"    {c['h']} vs {c['a']}: recorded {c['recorded'][0]}-{c['recorded'][1]} "
                      f"but sources say " +
                      ", ".join(f"{s}={v[0]}-{v[1]}" for s, v in c["sources_say"].items()) +
                      "  (recorded score left unchanged — fix results_log.json by hand if wrong)")
            else:
                print(f"    {c['h']} vs {c['a']}: " +
                      ", ".join(f"{s}={v[0]}-{v[1]}" for s, v in c["votes"].items()))

    single = [r for r in to_ingest if not r["confirmed"]]
    if to_ingest:
        print(f"\n{'Would ingest' if dry else 'Ingesting'} {len(to_ingest)} result(s):")
        for r in to_ingest:
            tag = "CONFIRMED" if r["confirmed"] else f"SINGLE({r['sources'][0]})"
            print(f"    {r['h']} {r['hg']}-{r['ag']} {r['a']}  [{tag}, src: {','.join(r['sources'])}]")
    else:
        print("\nNo new confirmed results this run.")

    if pending:
        print(f"\n{len(pending)} scheduled game(s) still pending (not final / not yet "
              f"past kickoff+buffer / awaiting a second source).")

    # Observability: make degraded cross-validation visible (it stays safe — the
    # kickoff gate still applies — but the operator should know).
    if n_ok < 2 and (to_ingest or pending):
        print(f"\n⚠️  WC26-DEGRADED-VALIDATION — only {n_ok} source(s) available this run; "
              f"results cannot be cross-validated until a second source returns.")
    if single and not dry:
        print(f"⚠️  {len(single)} result(s) ingested from a SINGLE source "
              f"({PRIMARY}) — not cross-validated; spot-check if a second feed stays down.")

    if not dry and to_ingest:
        added = append_results(to_ingest)
        print(f"\nAppended {added} result(s) to results_log.json.")
    elif dry:
        print("\n(dry-run — nothing written)")

    # exit 2 signals a conflict for the caller to alert on; results are still safe
    # (conflicts are never ingested), so this does not block a publish of the rest.
    return 2 if conflicts else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

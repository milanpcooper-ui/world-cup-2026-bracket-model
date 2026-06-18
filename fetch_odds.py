#!/usr/bin/env python3
"""Fetch betting odds deterministically from real markets (no LLM, no guessing) and
write the model's two odds inputs:

  * match_odds.json — per-game 1X2 lines for upcoming group games, from ESPN's
    scoreboard (the same free feed fetch_results.py uses; DraftKings moneylines,
    inline, no key). American odds -> implied prob -> de-vig (normalize to sum 1).
  * odds.json — title-winner implied probabilities, from Polymarket's public
    "World Cup Winner" market (Gamma API, no key). Each team's Yes price is its
    implied win prob; de-vigged by normalizing across the 48 mapped WC teams
    (non-team "Field"/placeholder outcomes are excluded from the denominator).

ESPN exposes no World Cup winner futures, so the title odds come from the prediction
market instead (Polymarket; Kalshi's KXMWORLDCUP series is an alternative). Both
files are written from live market data with no model judgement involved.

Usage:
    python3 fetch_odds.py             # write match_odds.json and odds.json
    python3 fetch_odds.py --dry-run   # preview only; write nothing
    python3 fetch_odds.py --match     # only match_odds.json
    python3 fetch_odds.py --title     # only odds.json
"""
import os, sys, json, datetime

import data as D
from fetch_results import FIFA_TO_CANON, canon_from_name, _get_json, GROUP_START, GROUP_END

HERE = os.path.dirname(os.path.abspath(__file__))
MATCH_ODDS = os.path.join(HERE, "match_odds.json")
ODDS_JSON = os.path.join(HERE, "odds.json")
LOOKAHEAD_DAYS = 8       # how far forward to pull upcoming-game lines
WINNER_SLUG = "world-cup-winner"   # Polymarket event slug for the title market
TITLE_MIN_PROB = 0.005   # drop near-zero longshots from odds.json for a clean file
# Only rewrite an odds file when the market moved at least this much (so quiet runs
# are a no-op and don't spam rebuilds/commits with sub-noise drift).
TITLE_MOVE = 0.005       # 0.5 pp on any title prob
MATCH_MOVE = 0.01        # 1 pp on any 1X2 leg


def american_to_prob(odds):
    """American moneyline (e.g. '+600', '-190') -> raw implied win probability."""
    ml = float(str(odds).replace("+", "").strip())
    return 100.0 / (ml + 100.0) if ml >= 0 else (-ml) / (-ml + 100.0)


def devig_1x2(p_home, p_draw, p_away):
    """Normalize three raw implied probabilities to sum 1 (proportional de-vig)."""
    s = p_home + p_draw + p_away
    if s <= 0:
        return None
    return round(p_home / s, 3), round(p_draw / s, 3), round(p_away / s, 3)


def _forward_dates():
    """YYYYMMDD ET dates from today through today+LOOKAHEAD, clamped to the group stage."""
    today_et = (datetime.datetime.now(datetime.timezone.utc)
                - datetime.timedelta(hours=4)).date()
    lo = max(GROUP_START, today_et)
    hi = min(GROUP_END, today_et + datetime.timedelta(days=LOOKAHEAD_DAYS))
    out, d = [], lo
    while d <= hi:
        out.append(d.strftime("%Y%m%d"))
        d += datetime.timedelta(days=1)
    return out


def _ml_close(side):
    """Pull the current ('close', falling back to 'open') American odds for one side
    of ESPN's inline moneyline object."""
    if not isinstance(side, dict):
        return None
    leg = side.get("close") or side.get("open") or {}
    return leg.get("odds")


def _group_fixtures():
    """{frozenset({h,a}): (h, a)} for every scheduled group game, fixture orientation."""
    return {frozenset((r[0], r[1])): (r[0], r[1]) for r in D.GROUP_FIXTURES}


def fetch_match_odds():
    """Return (lines, n_games_seen). `lines` is a list of match_odds.json entries for
    upcoming (state 'pre') group games that have a complete 1X2 moneyline."""
    fixtures = _group_fixtures()
    lines, seen = {}, 0
    for d in _forward_dates():
        data = _get_json(
            f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates={d}")
        if data is None:
            continue
        for ev in data.get("events", []):
            comp = (ev.get("competitions") or [{}])[0]
            st = (ev.get("status") or {}).get("type") or {}
            if st.get("state") != "pre":          # only upcoming, unplayed games
                continue
            teams = {}
            for c in comp.get("competitors", []):
                teams[c.get("homeAway")] = FIFA_TO_CANON.get((c.get("team") or {}).get("abbreviation"))
            eh, ea = teams.get("home"), teams.get("away")
            if not eh or not ea:
                continue
            key = frozenset((eh, ea))
            if key not in fixtures:               # group games only
                continue
            seen += 1
            ml = ((comp.get("odds") or [{}])[0]).get("moneyline") or {}
            oh, odr, oa = _ml_close(ml.get("home")), _ml_close(ml.get("draw")), _ml_close(ml.get("away"))
            if oh is None or odr is None or oa is None:
                continue
            try:
                dv = devig_1x2(american_to_prob(oh), american_to_prob(odr), american_to_prob(oa))
            except (TypeError, ValueError):
                continue
            if dv is None:
                continue
            ph, pd, pa = dv
            fh, fa = fixtures[key]
            # orient to the fixture's (home, away): home-prob must be P(fh wins)
            if eh == fh:
                home, away = ph, pa
            else:
                home, away = pa, ph
            lines[key] = {"h": fh, "a": fa, "home": home, "draw": pd, "away": away,
                          "_src": f"DraftKings via ESPN, close, {d[4:6]}/{d[6:]}"}
    return list(lines.values()), seen


def fetch_title_odds():
    """Return {canonical_team: implied_title_prob} from Polymarket's public
    "World Cup Winner" market, de-vigged. None if the market can't be read."""
    data = _get_json(f"https://gamma-api.polymarket.com/events?slug={WINNER_SLUG}")
    if not data:
        return None
    ev = data[0] if isinstance(data, list) else data
    markets = ev.get("markets", []) if isinstance(ev, dict) else []
    raw, total = {}, 0.0
    for m in markets:
        team = m.get("groupItemTitle")  # the team name for this outcome
        try:
            prices = json.loads(m.get("outcomePrices") or "[]")
        except (TypeError, ValueError):
            prices = []
        if not prices:
            continue
        try:
            yes = float(prices[0])      # P(Yes) = implied P(team wins)
        except (TypeError, ValueError):
            continue
        canon = canon_from_name(team) if team else None
        if canon:
            raw[canon] = raw.get(canon, 0.0) + yes
            total += yes                # de-vig denominator = real WC teams ONLY.
            # Non-team outcomes (Polymarket "Field"/"Other"/playoff placeholders,
            # eliminated nations) are excluded from both numerator and denominator,
            # so a future bucket carrying real mass can't bias the kept teams down.
            # model.py fit_ratings targets these as ABSOLUTE probs, so the scale
            # matters: the 48 mapped teams sum to ~1 (vig removed); listing only the
            # >=TITLE_MIN_PROB teams leaves the longshot mass unlisted, matching the
            # data.py default MARKET_TITLE_PROB convention (~0.99 over the top teams).
    if total <= 0 or not raw:
        return None
    probs = {t: round(p / total, 4) for t, p in raw.items()}  # de-vig over WC field
    return {t: p for t, p in probs.items() if p >= TITLE_MIN_PROB}


def _load_json(path):
    try:
        return json.load(open(path))
    except Exception:
        return None


def _title_changed(new, old):
    """True if odds.json should be rewritten (team set changed or any prob moved
    >= TITLE_MOVE)."""
    if not isinstance(old, dict):
        return True
    if set(new) != set(old):
        return True
    return any(abs(new[t] - float(old.get(t, -9))) >= TITLE_MOVE for t in new)


def _match_changed(new_lines, old):
    """True if match_odds.json should be rewritten (game set changed or any 1X2
    leg moved >= MATCH_MOVE)."""
    if not isinstance(old, list):
        return True
    def idx(rows):
        return {frozenset((r["h"], r["a"])): r for r in rows
                if isinstance(r, dict) and "h" in r and "a" in r}
    n, o = idx(new_lines), idx(old)
    if set(n) != set(o):
        return True
    for k, r in n.items():
        oo = o[k]
        if any(abs(float(r[f]) - float(oo.get(f, -9))) >= MATCH_MOVE
               for f in ("home", "draw", "away")):
            return True
    return False


def main(argv):
    dry = "--dry-run" in argv
    do_match = "--title" not in argv
    do_title = "--match" not in argv
    rc = 0

    if do_match:
        lines, seen = fetch_match_odds()
        print(f"[match_odds] upcoming games seen: {seen} | priced lines built: {len(lines)}")
        for L in lines:
            print(f"  {L['h']} vs {L['a']}: {L['home']}/{L['draw']}/{L['away']}  ({L['_src']})")
        if not lines:
            print("  no upcoming-game lines available — leaving match_odds.json unchanged.")
        elif dry:
            print("  (dry-run — match_odds.json not written)")
        elif not _match_changed(lines, _load_json(MATCH_ODDS)):
            print("  no material move since last write — match_odds.json unchanged.")
        else:
            with open(MATCH_ODDS, "w") as f:
                json.dump(lines, f, indent=2); f.write("\n")
            print(f"  wrote {len(lines)} line(s) to match_odds.json.")

    if do_title:
        probs = fetch_title_odds()
        if not probs:
            print("\n[odds] could not read the Polymarket title market — leaving odds.json unchanged.")
            rc = rc or 1
        else:
            print(f"\n[odds] title-winner implied probs ({len(probs)} teams):")
            for t, p in sorted(probs.items(), key=lambda kv: -kv[1]):
                print(f"  {t:18s} {p*100:5.1f}%")
            if dry:
                print("  (dry-run — odds.json not written)")
            elif not _title_changed(probs, _load_json(ODDS_JSON)):
                print("  no material move since last write — odds.json unchanged.")
            else:
                with open(ODDS_JSON, "w") as f:
                    json.dump(dict(sorted(probs.items(), key=lambda kv: -kv[1])), f, indent=2)
                    f.write("\n")
                print(f"  wrote {len(probs)} team(s) to odds.json.")

    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

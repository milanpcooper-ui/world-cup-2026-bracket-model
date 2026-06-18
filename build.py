"""Run the model and export results.json for the dashboard."""
import os, json, datetime
import numpy as np
import data as D
import model as M

HERE = os.path.dirname(os.path.abspath(__file__))
FIT_ITERS = 12
FIT_SIMS = 8000
FINAL_SIMS = 40000

def current_standings():
    """Group tables from completed RESULTS only (played-so-far)."""
    tables = {}
    for g, teams in D.GROUPS.items():
        row = {t: dict(mp=0, w=0, d=0, l=0, gf=0, ga=0, pts=0) for t in teams}
        for (h, a, hg, ag) in D.RESULTS:
            if h in row and a in row and D.TEAM_GROUP[h] == g:
                for t, sf, sa in ((h, hg, ag), (a, ag, hg)):
                    r = row[t]; r["mp"] += 1; r["gf"] += sf; r["ga"] += sa
                    if sf > sa: r["w"] += 1; r["pts"] += 3
                    elif sf == sa: r["d"] += 1; r["pts"] += 1
                    else: r["l"] += 1
        ordered = sorted(teams, key=lambda t: (row[t]["pts"], row[t]["gf"]-row[t]["ga"], row[t]["gf"]), reverse=True)
        tables[g] = [{"team": t, **row[t], "gd": row[t]["gf"]-row[t]["ga"]} for t in ordered]
    return tables

def merge_results_log():
    """Merge newly-finished results appended to results_log.json (list of
    {h,a,hg,ag}) into the live results set, then refresh the model's match map.
    This lets the nightly updater add scores without editing code."""
    path = os.path.join(HERE, "results_log.json")
    if not os.path.exists(path):
        return 0
    try:
        log = json.load(open(path))
    except Exception:
        return 0
    have = {frozenset((h, a)) for (h, a, _, _) in D.RESULTS}
    added = 0
    for e in log:
        h, a, hg, ag = e["h"], e["a"], int(e["hg"]), int(e["ag"])
        if frozenset((h, a)) not in have:
            D.RESULTS.append((h, a, hg, ag)); have.add(frozenset((h, a))); added += 1
    if added:
        M.GROUP_MATCHES = M.build_group_matches()  # refresh fixed scores
    return added

def merge_odds():
    """Override MARKET_TITLE_PROB from odds.json {team: implied_prob} if present,
    so the nightly run calibrates to the latest betting market each day."""
    path = os.path.join(HERE, "odds.json")
    if not os.path.exists(path):
        return 0
    try:
        od = json.load(open(path))
    except Exception:
        return 0
    od = {k: float(v) for k, v in od.items() if k in D.TEAM_GROUP and 0 < float(v) < 1}
    if od:
        D.MARKET_TITLE_PROB = od
    return len(od)

def merge_match_odds():
    """Load per-game 1X2 odds from match_odds.json (list of
    {h,a,home,draw,away} implied probabilities) into D.MATCH_ODDS so scheduled,
    unplayed group games are priced directly off the betting market."""
    path = os.path.join(HERE, "match_odds.json")
    if not os.path.exists(path):
        return 0
    try:
        arr = json.load(open(path))
    except Exception:
        return 0
    mo = {}
    played = {frozenset((h, a)) for (h, a, _, _) in D.RESULTS}
    for e in arr:
        h, a = e.get("h"), e.get("a")
        if h not in D.TEAM_GROUP or a not in D.TEAM_GROUP:
            continue
        if D.TEAM_GROUP[h] != D.TEAM_GROUP[a]:
            continue
        if frozenset((h, a)) in played:        # a result supersedes the line
            continue
        try:
            ph, pd, pa = float(e["home"]), float(e["draw"]), float(e["away"])
        except (KeyError, TypeError, ValueError):
            continue
        if ph > 0 and pd > 0 and pa > 0:
            mo[frozenset((h, a))] = {"h": h, "a": a, "home": ph, "draw": pd, "away": pa}
    if mo:
        D.MATCH_ODDS = mo
    return len(mo)

def _build_time():
    """(utc_epoch_int, human_ET_string). Anchored to a real UTC instant and shown in
    true US Eastern regardless of the build machine's timezone, so the stamp is never
    mislabeled. The dashboard re-renders the epoch in each viewer's own local clock."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        et = now_utc.astimezone(ZoneInfo("America/New_York"))
        label = et.tzname() or "ET"
    except Exception:
        et = now_utc.astimezone(datetime.timezone(datetime.timedelta(hours=-4)))
        label = "EDT"
    return int(now_utc.timestamp()), et.strftime("%Y-%m-%d %H:%M ") + label

def main():
    # snapshot the previous output (if any) before we overwrite it, so we can
    # report exactly what moved this rebuild.
    prev = None
    prev_path = os.path.join(HERE, "results.json")
    if os.path.exists(prev_path):
        try:
            prev = json.load(open(prev_path))
        except Exception:
            prev = None

    added = merge_results_log()
    if added:
        print(f"Merged {added} new result(s) from results_log.json")
    nod = merge_odds()
    if nod:
        print(f"Loaded {nod} fresh title-odds from odds.json")
    nmo = merge_match_odds()
    if nmo:
        print(f"Loaded {nmo} per-game 1X2 line(s) from match_odds.json")
    M.GROUP_MATCHES = M.build_group_matches()  # rebuild after all merges
    print("Fitting ratings to market...")
    ratings = M.fit_ratings(iters=FIT_ITERS, fit_sims=FIT_SIMS, verbose=True)
    print(f"Running {FINAL_SIMS} simulations...")
    out = M.simulate(FINAL_SIMS, 1.0, np.random.default_rng(20260615), ratings=ratings, collect=True)
    teams = out["teams"]; n = out["n_sims"]; tidx = out["tidx"]
    occ = out["occ"]; reach = out["reach"]; finish = out["finish"]; pairs = out["pairs"]

    def topteams(mno, k=8):
        arr = occ[mno]
        idx = np.argsort(-arr)[:k]
        return [{"team": teams[i], "p": round(float(arr[i])/n, 4)} for i in idx if arr[i] > 0]

    def toppairs(mno, k=4):
        pr = sorted(pairs[mno].items(), key=lambda kv: -kv[1])[:k]
        return [{"a": teams[a], "b": teams[b], "p": round(c/n, 4)} for (a, b), c in pr]

    # team-level summary
    team_rows = []
    for i, t in enumerate(teams):
        g = D.TEAM_GROUP[t]
        fr = finish[g]
        team_rows.append({
            "team": t, "group": g, "rating": round(float(ratings[i])),
            "elo": D.ELO[t],
            "p_win_group": round(float(fr["win"][i])/n, 4),
            "p_runner": round(float(fr["run"][i])/n, 4),
            "p_third_q": round(float(fr["third_q"][i])/n, 4),
            "p_advance": round(float(reach["R32"][i])/n, 4),
            "p_r16": round(float(reach["R16"][i])/n, 4),
            "p_qf": round(float(reach["QF"][i])/n, 4),
            "p_sf": round(float(reach["SF"][i])/n, 4),
            "p_final": round(float(reach["FINAL"][i])/n, 4),
            "p_champ": round(float(reach["WIN"][i])/n, 4),
            # appearance probability in each knockout match
            "appear": {str(m): round(float(occ[m][i])/n, 4) for m in range(73, 105) if occ[m][i] > 0},
        })
    team_rows.sort(key=lambda r: -r["p_champ"])

    # match-level
    matches = {}
    for m in range(73, 105):
        city, date, ko = D.KO_INFO[m]
        matches[str(m)] = {
            "no": m, "round": D.ROUND_NAME[m], "city": city, "date": date, "time": ko,
            "slot": _slot_label(m),
            "top_teams": topteams(m, 8),
            "top_pairs": toppairs(m, 5),
            "elimination": True,
        }

    # England focus
    eng = tidx["England"]; er = out["eng_records"]
    eng_finish = {k: round(v/n, 4) for k, v in er.items()}
    # most likely match England plays in each round
    def eng_round_match(mnos):
        best = max(mnos, key=lambda m: occ[m][eng])
        return {"match": best, **dict(zip(("city","date","time"), D.KO_INFO[best])),
                "p": round(float(occ[best][eng])/n, 4),
                "round": D.ROUND_NAME[best]}
    england = {
        "finish": eng_finish,
        "p_advance": round(float(reach["R32"][eng])/n,4),
        "p_r16": round(float(reach["R16"][eng])/n,4),
        "p_qf": round(float(reach["QF"][eng])/n,4),
        "p_sf": round(float(reach["SF"][eng])/n,4),
        "p_final": round(float(reach["FINAL"][eng])/n,4),
        "p_champ": round(float(reach["WIN"][eng])/n,4),
        "r32": eng_round_match(range(73,89)),
        "r16": eng_round_match(range(89,97)),
        "qf": eng_round_match(range(97,101)),
        "sf": eng_round_match(range(101,103)),
        "appear": {str(m): round(float(occ[m][eng])/n,4) for m in range(73,105) if occ[m][eng]>0},
    }

    # calibration check (title odds)
    tp = M.title_probs_from(reach, teams, n)
    calib = [{"team": t, "market": D.MARKET_TITLE_PROB[t], "model": round(tp.get(t,0),4)}
             for t in sorted(D.MARKET_TITLE_PROB, key=lambda x:-D.MARKET_TITLE_PROB[x])]

    # calibration check (per-game 1X2): confirm the engine reproduces each
    # priced game's market line via the solved Poisson means.
    match_calib = []
    for o in D.MATCH_ODDS.values():
        s = o["home"] + o["draw"] + o["away"]
        mh, md, ma = o["home"]/s, o["draw"]/s, o["away"]/s
        la, lb = M.lambdas_from_wdl(o["home"], o["draw"], o["away"])
        ph, pd, pw = M._wdl(la, lb)
        match_calib.append({"h": o["h"], "a": o["a"], "group": D.TEAM_GROUP[o["h"]],
                            "market": [round(mh,3), round(md,3), round(ma,3)],
                            "model":  [round(ph,3), round(pd,3), round(pw,3)],
                            "lambdas": [round(la,2), round(lb,2)]})

    _epoch, _stamp = _build_time()
    result = {
        "generated": _stamp,
        "generated_epoch": _epoch,
        "n_sims": n,
        "groups": D.GROUPS,
        "standings": current_standings(),
        "results_played": [{"h":h,"a":a,"hg":hg,"ag":ag,"g":D.TEAM_GROUP[h]} for (h,a,hg,ag) in D.RESULTS],
        "teams": team_rows,
        "matches": matches,
        "england": england,
        "calibration": calib,
        "match_calibration": match_calib,
        "ko_info": {str(m): {"city":c,"date":d,"time":t,"round":D.ROUND_NAME[m]}
                    for m,(c,d,t) in D.KO_INFO.items()},
        "bracket": _bracket_struct(),
        "assumptions": ASSUMPTIONS,
    }
    # what changed vs the previous build
    result["changes"] = compute_changes(prev, result)
    if prev is not None:
        with open(os.path.join(HERE, "results_prev.json"), "w") as f:
            json.dump(prev, f)
    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(result, f)
    print("Wrote results.json")
    # quick sanity print
    print("\nChampion top 8:")
    for r in team_rows[:8]:
        print(f"  {r['team']:12s} champ {r['p_champ']*100:4.1f}%  SF {r['p_sf']*100:4.1f}%  adv {r['p_advance']*100:5.1f}%")
    print(f"\nEngland: win L {eng_finish['win_L']*100:.0f}% | RU L {eng_finish['run_L']*100:.0f}% "
          f"| 3rd {eng_finish['third_L']*100:.0f}% | out {eng_finish['out']*100:.0f}%")
    print(f"England most likely R32: M{england['r32']['match']} {england['r32']['city']} "
          f"{england['r32']['date']} (p={england['r32']['p']:.2f})")
    print(f"England most likely R16: M{england['r16']['match']} {england['r16']['city']} "
          f"{england['r16']['date']} (p={england['r16']['p']:.2f})")
    if match_calib:
        print(f"\nPer-game odds calibration ({len(match_calib)} game(s), market vs model H/D/A):")
        for c in match_calib:
            mk = "/".join(f"{x:.0%}" for x in c["market"])
            md = "/".join(f"{x:.0%}" for x in c["model"])
            print(f"  [{c['group']}] {c['h']:>11s} v {c['a']:<11s} market {mk:>14s}  model {md:>14s}")
    print_changes(result["changes"])
    return result

def _slot_label(m):
    for (mno, a, b, pool) in D.R32:
        if mno == m:
            sb = b if b != "3rd" else f"3rd({pool})"
            return f"{_sl(a)} vs {_sl(sb)}"
    fb = {**D.R16, **D.QF, **D.SF, 104: D.FINAL[104]}
    if m in fb:
        f1, f2 = fb[m]
        return f"W{f1} vs W{f2}"
    if m == 103:
        return "Losers SF1 vs SF2"
    return ""

def _sl(s):
    if s.startswith("3rd"): return s
    if s[0] == "1": return f"Winner {s[1]}"
    if s[0] == "2": return f"Runner-up {s[1]}"
    return s

# ---------------------------------------------------------------------------
# CHANGE TRACKING — diff this build against the previous results.json. Because
# the simulation uses fixed seeds, unchanged inputs reproduce identical numbers,
# so anything reported here is a real move driven by new results/odds.
# ---------------------------------------------------------------------------
CHANGE_DELTA = 0.02   # report probability shifts of >= 2 percentage points
ODDS_DELTA = 0.005    # report title-odds market moves of >= 0.5 pt as a driver
ARROW, UP, DOWN = "→", "▲", "▼"   # → ▲ ▼

def _eng_opponent(res, rnd):
    """Most-likely opponent (non-England team) in England's projected box for a round."""
    e = res.get("england", {}).get(rnd)
    if not e:
        return None
    m = res.get("matches", {}).get(str(e["match"]))
    if not m:
        return None
    for t in m.get("top_teams", []):
        if t["team"] != "England":
            return t["team"]
    return None

# Bracket cards the user actually sees as "Team A vs Team B" boxes (the 3rd-place
# game, M103, is a one-line note with no pairing shown, so it is not a box).
MATCH_BOXES = [m for m in range(73, 105) if m != 103]

def _displayed_pair(res, mno):
    """The matchup printed on a bracket box: its single most-likely exact pairing
    (top_pairs[0]). Returns (canonical_key, display_str, prob).
      - canonical_key is a side-order-independent tuple so 'A vs B' and 'B vs A'
        compare equal (only the teams matter, not which feeder slot they came from)
      - display_str preserves the order the box shows
    A box with no pairs yet reads ('', 'TBD', None); a box missing entirely from a
    build reads (None, None, None) so callers can skip it."""
    m = res.get("matches", {}).get(str(mno))
    if not m:
        return None, None, None
    tp = m.get("top_pairs") or []
    if not tp:
        return ("",), "TBD", None
    a, b = tp[0]["a"], tp[0]["b"]
    return tuple(sorted((a, b))), f"{a} vs {b}", tp[0].get("p")

# ---------------------------------------------------------------------------
# WHY ATTRIBUTION — given that fixed seeds make every output move traceable to a
# changed input, tie each bracket-box flip back to the specific results / odds
# that could have caused it. A box can only be reached by teams from certain
# groups, so an input change is a *candidate* driver for that box iff it touches
# one of those groups. Title-odds refits are global (they re-rate the whole
# field), so for those we rank the movers that involve the teams actually
# entering/leaving the box first, then fall back to the broad market refresh.
# ---------------------------------------------------------------------------

def _box_source_groups():
    """{match_no: set(group letters whose teams can appear in that box)}.
    R32 boxes read their slot defs (a group winner/runner-up, or a 3rd-place
    pool of groups); every later round is the union of its two feeders."""
    sg = {}
    for (mno, a, b, pool) in D.R32:
        groups = set()
        for slot in (a, b):
            if slot == "3rd":
                groups |= set(pool or "")     # pool is a string of group letters
            else:
                groups.add(slot[1])           # "1E" -> "E", "2A" -> "A"
        sg[mno] = groups
    for rnd in (D.R16, D.QF, D.SF, D.FINAL):  # ordered so feeders resolve first
        for mno, (f1, f2) in rnd.items():
            sg[mno] = sg.get(f1, set()) | sg.get(f2, set())
    return sg

def _pair_now_prob(match, disp):
    """Current probability of a 'A vs B' display string within `match`'s
    top_pairs (None if that pairing isn't listed). Lets us tell a settled flip
    from a near-tie: if the previously-shown pairing is still almost as likely
    now, the box basically coin-flipped rather than decisively moved."""
    if not disp or disp == "TBD" or " vs " not in disp:
        return None
    a, b = disp.split(" vs ")
    key = frozenset((a.strip(), b.strip()))
    for p in (match.get("top_pairs") or []):
        if frozenset((p["a"], p["b"])) == key:
            return p.get("p")
    return None

def _fmt_p(x):
    """Match the dashboard's pct(): no decimals at >=10%, one below."""
    if x is None:
        return "—"
    return f"{x*100:.0f}%" if x >= 0.1 else f"{x*100:.1f}%"

def _join(items):
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]

def _poss(name):
    """English possessive: Spain -> Spain's, Netherlands -> Netherlands'."""
    return name + ("'" if name.endswith("s") else "'s")

def _odds_np(m):
    word = "rise" if m["dir"] == "up" else "slide"
    return f"a {word} in {_poss(m['team'])} title odds ({_fmt_p(m['old'])}{ARROW}{_fmt_p(m['new'])})"

def _result_np(r):
    return f"{r['h']} {r['hg']}-{r['ag']} {r['a']} (Group {r['group']})"

def _result_cause(r):
    """Result phrased as a cause — flags a score correction so 'driven by the corrected
    Ghana 1-0 Panama' reads right."""
    return ("the corrected " if r.get("corrected") else "") + _result_np(r)

# A box fed by this many groups is so wide that no single result decides it — the
# whole-field title-odds refit is the honest attribution (QF/SF/Final draw from 7-12).
DEEP_BOX_GROUPS = 6

def _attribute(c, d_results, d_odds, d_lines, src, all_results, all_odds):
    """Return (why_sentence, cited_drivers) for a flipped box.

    `cited_drivers` holds ONLY the inputs the sentence actually pins the flip on, so
    the dashboard chips never imply a cause the prose didn't claim. We name a driver
    only when it genuinely constrains this box: an odds move on a team entering/leaving
    (and big enough to be visible at the displayed precision), a result involving such a
    team, or — for a narrow box — a result in one of its few feeder groups. Boxes fed by
    many groups (deep rounds) get the honest 'field-wide refit' framing instead of an
    arbitrary single input, because the holistic re-rate, not one score, moved them.

    `all_results`/`all_odds` are this build's FULL change set. When nothing touches the
    box's own feeder groups we fall back to them — a third-place reshuffle (Annex C) can
    carry a result in any group into a box outside its nominal pool, so the honest cause
    is 'whatever actually changed this build', not an assumed odds refresh."""
    entered, left = c.get("entered", []), c.get("left", [])
    movers_set = set(entered) | set(left)
    common = sorted(set(c_split(c["old"])) & set(c_split(c["new"])))
    new_p, old_now = c.get("new_p"), c.get("old_now_p")
    pairing = "final" if c.get("round") == "Final" else "pairing"
    deep = len(src) > DEEP_BOX_GROUPS

    # who moved — framed around the team that stayed when there is exactly one
    if len(common) == 1 and len(entered) == 1 and len(left) == 1:
        head = f"{entered[0]} replaces {left[0]} as {_poss(common[0])} projected opponent"
    elif entered and left:
        verb = "replace" if len(entered) > 1 else "replaces"
        head = f"{_join(entered)} {verb} {_join(left)} as the projected {pairing}"
    elif entered:
        head = f"{_join(entered)} {'move' if len(entered) > 1 else 'moves'} into this box"
    elif left:
        head = f"{_join(left)} {'drop' if len(left) > 1 else 'drops'} out of this box"
    else:
        head = "the projected pairing reshuffled"

    cause, cited = [], {"results": [], "odds": [], "lines": []}
    # only cite an odds move that's actually visible at the % precision we print, so we
    # never write "rose 11%->11%" (sub-display nudges fall through to the refit framing)
    visible = lambda m: _fmt_p(m["old"]) != _fmt_p(m["new"])
    riser_in = max((m for m in d_odds if m["team"] in entered and m["delta"] > 0 and visible(m)),
                   key=lambda m: m["delta"], default=None)
    faller_out = min((m for m in d_odds if m["team"] in left and m["delta"] < 0 and visible(m)),
                     key=lambda m: m["delta"], default=None)
    res_named = [r for r in d_results if r["h"] in movers_set or r["a"] in movers_set]

    if riser_in and faller_out:
        cause.append(f"{_odds_np(riser_in)} as {_poss(faller_out['team'])} slid "
                     f"{_fmt_p(faller_out['old'])}{ARROW}{_fmt_p(faller_out['new'])}")
        cited["odds"] = [riser_in, faller_out]
    elif riser_in:
        cause.append(_odds_np(riser_in)); cited["odds"] = [riser_in]
    elif faller_out:
        cause.append(_odds_np(faller_out)); cited["odds"] = [faller_out]
    if res_named:
        cause.append(_result_cause(res_named[0])); cited["results"] = [res_named[0]]
    for l in d_lines:
        if l["h"] in movers_set or l["a"] in movers_set:
            cause.append(f"a re-priced {l['h']}–{l['a']} betting line")
            cited["lines"] = [l]; break

    if not cause:   # nothing touched the entering/leaving teams directly
        if not deep and d_results:           # a narrow box: an in-feeder score constrains it
            cause.append(_result_cause(d_results[0])); cited["results"] = [d_results[0]]
        elif all_results and not all_odds:
            # results-only rebuild: with fixed seeds the score(s) are the only cause —
            # even for a box outside their groups (the knockout-seeding/Annex C reshuffle).
            if len(all_results) == 1:
                cause.append(_result_cause(all_results[0]) + ", reshuffling the knockout seeding")
                cited["results"] = [all_results[0]]
            else:
                cause.append("today's results, reshuffling the knockout seeding")
        elif all_odds and not all_results:
            cause.append("today's field-wide title-odds refit (many groups feed this box, "
                         "so no single result settles it)" if deep else "today's title-odds refresh")
        elif all_results and all_odds:
            cause.append("today's new results and the title-odds refresh")
        else:
            cause.append("the latest inputs")

    s = head + " — driven by " + _join(cause) + "."
    # confidence — a low top probability means wide-open (many near-equal pairings); only
    # call it a "narrow" two-way flip when the new pairing is a genuine leader.
    if new_p is not None:
        if new_p < 0.15:
            s += f" Still a wide-open slot (top {pairing} just {_fmt_p(new_p)}) — a lean, not a lock."
        elif old_now is not None and abs(new_p - old_now) < 0.03:
            s += f" Narrow call — the new {pairing} ({_fmt_p(new_p)}) barely edges the old ({_fmt_p(old_now)})."
    return s, cited

def c_split(disp):
    """Team names from an 'A vs B' display string ([] for TBD/blank)."""
    if not disp or disp == "TBD" or " vs " not in disp:
        return []
    return [x.strip() for x in disp.split(" vs ")]

def _build_summary(ch):
    """One-paragraph build-level context: what this rebuild ingested and how many
    bracket boxes changed. It deliberately does NOT rank results-vs-odds as the cause —
    with a holistic refit that can't be cleanly decomposed, the per-flip `why` lines
    carry the honest box-by-box attribution; this just sets the scene."""
    res = ch["drivers"]["results"]
    movers = ch["drivers"]["odds_movers"]
    lines = ch["drivers"]["line_moves"]
    n = len(ch.get("matchups", []))
    parts = []
    if res:
        nnew = [r for r in res if not r.get("corrected")]
        ncorr = [r for r in res if r.get("corrected")]
        labels = []
        if nnew:
            labels.append(f"{len(nnew)} new result{'s' if len(nnew) > 1 else ''}")
        if ncorr:
            labels.append(f"{len(ncorr)} corrected result{'s' if len(ncorr) > 1 else ''}")
        scorelines = "; ".join(_result_np(r) for r in res[:3])
        parts.append(f"{_join(labels)} ({scorelines}{'…' if len(res) > 3 else ''})")
    if movers:
        ups = [m for m in movers if m["dir"] == "up"][:2]
        downs = [m for m in movers if m["dir"] == "down"][:2]
        poss = "s'" if len(movers) > 1 else "'s"
        seg = f"a betting-market refresh that moved {len(movers)} team{poss} title odds"
        notable = []
        if ups:
            notable.append(", ".join(f"{m['team']} {UP}" for m in ups))
        if downs:
            notable.append(", ".join(f"{m['team']} {DOWN}" for m in downs))
        if notable:
            seg += " (" + "; ".join(notable) + ")"
        parts.append(seg)
    if lines:
        parts.append(f"{len(lines)} re-priced game line{'s' if len(lines) > 1 else ''}")
    if not parts:
        # boxes can't flip with truly-unchanged inputs (fixed seeds), but never claim
        # "unchanged" while showing flips — that contradiction is the bug we just fixed.
        return (f"{n} bracket {'box' if n == 1 else 'boxes'} shifted from the latest inputs."
                if n else "Inputs were unchanged — no material movement this rebuild.")
    lead = "This rebuild ingested " + _join(parts) + "."
    if n:
        lead += (f" {n} bracket {'box now shows' if n == 1 else 'boxes now show'} a different "
                 f"pairing — see each for what moved it.")
    return lead

def compute_changes(prev, cur):
    if not prev:
        return {"first_run": True}
    ch = {"first_run": False, "prev_generated": prev.get("generated"),
          "prev_generated_epoch": prev.get("generated_epoch"),
          "new_results": [], "matchups": [], "england_path": [], "opponents": [],
          "england_outlook": [], "title_movers": []}

    # ingested results: brand-new fixtures AND score corrections to an already-recorded
    # fixture (same teams, different score). Both move the bracket — and a correction must
    # be caught, or a correction-only rebuild looks like "no change" while boxes quietly flip.
    pmap = {(r["h"], r["a"]): (r["hg"], r["ag"]) for r in prev.get("results_played", [])}
    new_res = []
    for r in cur.get("results_played", []):
        key = (r["h"], r["a"])
        corrected = key in pmap and pmap[key] != (r["hg"], r["ag"])
        if key not in pmap or corrected:
            tag = " · corrected" if corrected else ""
            ch["new_results"].append(f'{r["h"]} {r["hg"]}-{r["ag"]} {r["a"]} (Grp {r["g"]}{tag})')
            new_res.append({"h": r["h"], "a": r["a"], "hg": r["hg"], "ag": r["ag"],
                            "group": r["g"], "corrected": corrected})

    # bracket matchup changes — which knockout boxes now show a *different*
    # pairing than the last build. This is keyed off the displayed top pairing
    # only: if the odds move but 'Team A vs Team B' is unchanged, nothing is
    # reported here (that's the whole point — track who's projected into each box
    # for ticket planning, not every probability wiggle). Sorted by match number
    # so it reads R32 -> Final, i.e. soonest (most ticket-urgent) games first.
    for mno in MATCH_BOXES:
        pk, pdisp, pp = _displayed_pair(prev, mno)
        ck, cdisp, cp = _displayed_pair(cur, mno)
        if pdisp is None or cdisp is None:
            continue  # box absent from one of the builds — nothing to compare
        if pk != ck:
            cm = cur["matches"][str(mno)]
            ch["matchups"].append({
                "match": mno, "round": cm["round"], "city": cm["city"], "date": cm["date"],
                "old": pdisp, "new": cdisp, "old_p": pp, "new_p": cp})

    # ---- WHY each matchup flipped: attribute it to the inputs that changed ----
    # The three input categories that moved this rebuild, read straight off the
    # snapshots so attribution is exact (fixed seeds => every move is one of these).
    pmkt = {c["team"]: c["market"] for c in prev.get("calibration", [])}
    odds_movers = []
    for c in cur.get("calibration", []):
        o = pmkt.get(c["team"]); nv = c["market"]
        if o is not None and abs(nv - o) >= ODDS_DELTA:
            odds_movers.append({"team": c["team"], "group": D.TEAM_GROUP.get(c["team"], "?"),
                                "old": o, "new": nv, "delta": round(nv - o, 4),
                                "dir": "up" if nv > o else "down"})
    odds_movers.sort(key=lambda m: -abs(m["delta"]))

    pline = {(c["h"], c["a"]): c["market"] for c in prev.get("match_calibration", [])}
    line_moves = []
    for c in cur.get("match_calibration", []):
        o = pline.get((c["h"], c["a"]))
        if o is not None and o != c["market"]:
            line_moves.append({"h": c["h"], "a": c["a"], "group": c.get("group", "?"),
                               "old": o, "new": c["market"]})

    ch["drivers"] = {"results": new_res, "odds_movers": odds_movers, "line_moves": line_moves}

    src_groups = _box_source_groups()
    for c in ch["matchups"]:
        mno = c["match"]
        src = src_groups.get(mno, set())
        old_pair = set(c["old"].split(" vs ")) if c["old"] and c["old"] != "TBD" else set()
        new_pair = set(c["new"].split(" vs ")) if c["new"] and c["new"] != "TBD" else set()
        c["entered"] = sorted(new_pair - old_pair)
        c["left"] = sorted(old_pair - new_pair)
        c["source_groups"] = sorted(src)
        c["old_now_p"] = _pair_now_prob(cur["matches"][str(mno)], c["old"])
        # candidate inputs = those touching a group that feeds this box; _attribute
        # picks the subset it can honestly pin the flip on and returns only those.
        d_results = [r for r in new_res if r["group"] in src]
        d_odds = [m for m in odds_movers if m["group"] in src]
        d_lines = [l for l in line_moves if l["group"] in src]
        c["why"], c["drivers"] = _attribute(c, d_results, d_odds, d_lines, src, new_res, odds_movers)

    # England projected route (venue / date / match number) per round
    for rnd, label in [("r32", "Round of 32"), ("r16", "Round of 16"),
                       ("qf", "Quarterfinal"), ("sf", "Semifinal")]:
        pe = prev.get("england", {}).get(rnd); ce = cur.get("england", {}).get(rnd)
        if pe and ce and (pe["city"] != ce["city"] or pe["date"] != ce["date"] or pe["match"] != ce["match"]):
            ch["england_path"].append({"round": label,
                "old": f'{pe["city"]} {pe["date"]} (M{pe["match"]})',
                "new": f'{ce["city"]} {ce["date"]} (M{ce["match"]})'})

    # England likely opponent in the two nearest rounds
    for rnd, label in [("r32", "Round of 32"), ("r16", "Round of 16")]:
        o = _eng_opponent(prev, rnd); n = _eng_opponent(cur, rnd)
        if o and n and o != n:
            ch["opponents"].append({"round": label, "old": o, "new": n})

    # England outlook shifts
    pe = prev.get("england", {}); ce = cur.get("england", {})
    pf = pe.get("finish", {}); cf = ce.get("finish", {})
    metrics = [("Win Group L", pf.get("win_L"), cf.get("win_L")),
               ("Runner-up L", pf.get("run_L"), cf.get("run_L")),
               ("3rd & qualify", pf.get("third_L"), cf.get("third_L")),
               ("Eliminated in groups", pf.get("out"), cf.get("out")),
               ("Reach R16", pe.get("p_r16"), ce.get("p_r16")),
               ("Reach QF", pe.get("p_qf"), ce.get("p_qf")),
               ("Reach SF", pe.get("p_sf"), ce.get("p_sf")),
               ("Reach final", pe.get("p_final"), ce.get("p_final")),
               ("Win it all", pe.get("p_champ"), ce.get("p_champ"))]
    for name, o, n in metrics:
        if o is not None and n is not None and abs(n - o) >= CHANGE_DELTA:
            ch["england_outlook"].append({"metric": name, "old": o, "new": n})

    # title-odds movers
    pc = {t["team"]: t["p_champ"] for t in prev.get("teams", [])}
    for t in cur.get("teams", []):
        o = pc.get(t["team"]); n = t["p_champ"]
        if o is not None and abs(n - o) >= CHANGE_DELTA:
            ch["title_movers"].append({"team": t["team"], "old": o, "new": n})
    ch["title_movers"].sort(key=lambda d: -abs(d["new"] - d["old"]))

    ch["summary"] = _build_summary(ch)
    return ch

def print_changes(ch):
    print("\n=== WHAT CHANGED SINCE LAST BUILD ===")
    if ch.get("first_run"):
        print("  Baseline build — no previous version to compare.")
        return
    if ch.get("prev_generated"):
        print(f"  (vs build generated {ch['prev_generated']})")
    if ch.get("summary"):
        print(f"  {ch['summary']}")
    shown = False
    if ch["new_results"]:
        shown = True; print("  New results ingested:")
        for s in ch["new_results"]:
            print(f"    + {s}")
    if ch.get("matchups"):
        shown = True
        print(f"  Bracket matchups changed ({len(ch['matchups'])} box(es) now show a different pairing):")
        for c in ch["matchups"]:
            op = f" ({c['old_p']*100:.0f}%)" if c.get("old_p") is not None else ""
            np_ = f" ({c['new_p']*100:.0f}%)" if c.get("new_p") is not None else ""
            print(f"    M{c['match']} {c['round']} · {c['city']} {c['date']}: {c['old']}{op}  ->  {c['new']}{np_}")
            if c.get("why"):
                print(f"        why: {c['why']}")
    if ch["england_path"]:
        shown = True; print("  England projected route changed:")
        for c in ch["england_path"]:
            print(f"    {c['round']}: {c['old']}  ->  {c['new']}")
    if ch["opponents"]:
        shown = True; print("  England likely opponent changed:")
        for c in ch["opponents"]:
            print(f"    {c['round']}: {c['old']}  ->  {c['new']}")
    if ch["england_outlook"]:
        shown = True; print("  England outlook shifts (>=2 pts):")
        for c in ch["england_outlook"]:
            print(f"    {c['metric']}: {c['old']*100:.0f}%  ->  {c['new']*100:.0f}%")
    if ch["title_movers"]:
        shown = True; print("  Title-odds movers (>=2 pts):")
        for c in ch["title_movers"][:8]:
            arrow = "up" if c["new"] > c["old"] else "down"
            print(f"    {c['team']}: {c['old']*100:.1f}%  ->  {c['new']*100:.1f}%  ({arrow})")
    if not shown:
        print("  No material changes (inputs unchanged or moves below 2 pts).")

def _bracket_struct():
    return {
        "R32": [m for m in range(73,89)],
        "R16": list(D.R16.keys()),
        "QF": list(D.QF.keys()),
        "SF": list(D.SF.keys()),
        "F": [104], "feed": {**{str(k):v for k,v in D.R16.items()},
                             **{str(k):v for k,v in D.QF.items()},
                             **{str(k):v for k,v in D.SF.items()},
                             "104":[101,102]},
        "r32slots": {str(mno): [a, (f"3rd:{pool}" if b=="3rd" else b)] for (mno,a,b,pool) in D.R32},
    }

ASSUMPTIONS = [
    "Match engine: independent Poisson goals; each team's expected goals set by the Elo-rating gap (host nations +50 Elo).",
    "Top teams' strength is fitted to the betting market's title odds (Kalshi via Covers, 13 Jun 2026); the rest of the field is set by world-football Elo (15 Jun 2026).",
    "Second calibration input: any scheduled but unplayed group game that has a betting line in match_odds.json is priced directly off the market's 1X2 (home/draw/away) odds — the model solves the Poisson scoring rates that reproduce that line — instead of inferring the game from the Elo gap.",
    "Completed results so far are locked in; all remaining group games and every knockout tie are simulated.",
    "Knockout ties level after 90' are resolved by an Elo-logistic extra-time/penalty model.",
    "Best-8 third-placed teams allocated to bracket slots using FIFA's exact Annex C table (495 combinations).",
    f"Probabilities from {FINAL_SIMS:,} Monte Carlo tournament simulations; sampling error on a 50% probability is about ±0.3%.",
    "A few lower-tier teams' Elo values are estimated (flagged in data); they barely affect the knockout picture and refine as results post.",
]

if __name__ == "__main__":
    main()

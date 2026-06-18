"""
2026 World Cup Monte Carlo model.

Engine:  goals drawn from independent Poisson per team; each team's expected
goals come from the Elo difference (host bonus added). Group standings ranked
by points -> goal difference -> goals for -> random. Best-8 third-place teams
allocated to the bracket using FIFA's exact Annex C table. Knockout matches
resolved at 90' by Poisson; ties broken by an Elo-logistic ET/penalty model.

Calibration: a single spread multiplier on the Elo differences is fitted so the
simulated title probabilities match the betting market's top teams (Kalshi/Covers,
13 Jun 2026). This anchors the model on the market, per the brief, while Elo gives
discrimination across the full 48-team field.
"""
import os, itertools
import numpy as np
import data as D

HERE = os.path.dirname(os.path.abspath(__file__))
TOTAL_GROUP = 2.6      # avg combined goals, group game
TOTAL_KO = 2.5         # avg combined goals, knockout 90'
SUPREMACY_SCALE = 300  # Elo points per ~1 goal of supremacy (before spread)
HOST_BONUS = 50        # Elo bump for host nations (USA/MEX/CAN), all matches

# ---------------------------------------------------------------------------
def load_annexC():
    """frozenset(8 group letters) -> list of 8 group letters for slots
       [1A,1B,1D,1E,1G,1I,1K,1L] (the group whose 3rd-place team fills each).
       Compact format: whitespace-separated 16-char tokens; first 8 chars are
       the qualifying-third groups (the key), last 8 are the slot assignments."""
    table = {}
    with open(os.path.join(HERE, "annexC.txt")) as f:
        text = f.read()
    for tok in text.split():
        tok = tok.strip()
        if len(tok) != 16:
            continue
        table[frozenset(tok[:8])] = list(tok[8:])
    return table

ANNEXC = load_annexC()

def eff_elo(team):
    e = D.ELO[team]
    if team in D.HOSTS:
        e += HOST_BONUS
    return e

# Precompute group match lists: per group, list of (i,j,fixedscore_or_None)
def build_group_matches():
    res = {}
    fixed = {}
    for (h, a, hg, ag) in D.RESULTS:
        fixed[frozenset((h, a))] = (h, a, hg, ag)
    mo = getattr(D, "MATCH_ODDS", {}) or {}
    for g, teams in D.GROUPS.items():
        idx = {t: k for k, t in enumerate(teams)}
        matches = []
        for h, a in itertools.combinations(teams, 2):
            key = frozenset((h, a))
            raw = fixed.get(key)
            fs = None      # fixed final score (played game)
            fl = None      # market-derived (lambda_home, lambda_away) for this (h,a)
            if raw is not None:
                # re-orient the stored (home,away,hg,ag) to this (h,a) order
                hg, ag = (raw[2], raw[3]) if raw[0] == h else (raw[3], raw[2])
                fs = (h, a, hg, ag)
            elif key in mo:
                o = mo[key]
                # orient the stored 1X2 to this (h,a) order
                if o["h"] == h:
                    ph, pd, pa = o["home"], o["draw"], o["away"]
                else:
                    ph, pd, pa = o["away"], o["draw"], o["home"]
                fl = lambdas_from_wdl(ph, pd, pa)
            matches.append((idx[h], idx[a], h, a, fs, fl))
        res[g] = (teams, matches)
    return res

GROUP_MATCHES = build_group_matches()

# ---------------------------------------------------------------------------
def poisson_lambdas(elo_a, elo_b, total, spread):
    sup = spread * (elo_a - elo_b) / SUPREMACY_SCALE
    la = np.clip(total / 2 + sup / 2, 0.18, 6.0)
    lb = np.clip(total / 2 - sup / 2, 0.18, 6.0)
    return la, lb

# ---------------------------------------------------------------------------
# Market 1X2 -> Poisson means. Lets a scheduled game be priced directly off the
# betting market instead of the Elo gap (a second calibration input).
# ---------------------------------------------------------------------------
def _pois_pmf(lam, cap):
    pmf = np.empty(cap + 1)
    pmf[0] = np.exp(-lam)
    for k in range(1, cap + 1):
        pmf[k] = pmf[k - 1] * lam / k
    return pmf

def _wdl(la, lb, cap=14):
    """Home/draw/away probabilities for two independent Poisson goal counts."""
    M = np.outer(_pois_pmf(la, cap), _pois_pmf(lb, cap))  # M[i,j]=P(home=i,away=j)
    pd = float(np.trace(M))
    ph = float(np.tril(M, -1).sum())   # home goals > away goals
    pw = float(np.triu(M, 1).sum())    # away win
    return ph, pd, pw

def lambdas_from_wdl(p_home, p_draw, p_away, cap=14, iters=50):
    """Solve independent-Poisson means (la, lb) that reproduce a market's
    1X2 probabilities. Inputs are de-vigged by normalizing to sum 1. Uses a
    2-D Newton step on (la, lb) matching home-win and away-win probabilities;
    the draw probability follows by complement."""
    s = p_home + p_draw + p_away
    p_home, p_away = p_home / s, p_away / s
    la = lb = TOTAL_GROUP / 2.0
    for _ in range(iters):
        ph, pd, pw = _wdl(la, lb, cap)
        f = np.array([ph - p_home, pw - p_away])
        if np.max(np.abs(f)) < 1e-7:
            break
        e = 1e-4
        ph1, _, pw1 = _wdl(la + e, lb, cap)
        ph2, _, pw2 = _wdl(la, lb + e, cap)
        J = np.array([[(ph1 - ph) / e, (ph2 - ph) / e],
                      [(pw1 - pw) / e, (pw2 - pw) / e]])
        try:
            d = np.linalg.solve(J, -f)
        except np.linalg.LinAlgError:
            break
        la = float(np.clip(la + d[0], 0.05, 7.0))
        lb = float(np.clip(lb + d[1], 0.05, 7.0))
    return la, lb

def base_ratings():
    teams = D.ALL_TEAMS
    return np.array([eff_elo(t) for t in teams], dtype=float)

def simulate(n_sims, spread, rng, ratings=None, collect=False):
    """Run n_sims tournaments. Returns dict of tallies.
    `ratings` = optional np array (len = #teams) of effective Elo to use."""
    teams = D.ALL_TEAMS
    tidx = {t: i for i, t in enumerate(teams)}
    NT = len(teams)
    if ratings is None:
        ratings = base_ratings()

    # ---- GROUP STAGE ----
    # per group arrays: pts, gd, gf  shape (n_sims, 4)
    group_rank_team = {}   # g -> array (n_sims,4) team-name-index by finishing pos 0..3
    third_stats = {}       # g -> (pts,gd,gf) arrays (n_sims,) for the 3rd-placed team
    win_idx = {}; run_idx = {}; third_idx = {}
    for g, (gteams, matches) in GROUP_MATCHES.items():
        pts = np.zeros((n_sims, 4)); gf = np.zeros((n_sims, 4)); ga = np.zeros((n_sims, 4))
        elos = [ratings[tidx[t]] for t in gteams]
        for (i, j, hn, an, fs, fl) in matches:
            if fs is not None:
                gi = np.full(n_sims, fs[2]); gj = np.full(n_sims, fs[3])
            elif fl is not None:
                # market-priced game: use Poisson means solved from the 1X2 line
                gi = rng.poisson(fl[0], n_sims); gj = rng.poisson(fl[1], n_sims)
            else:
                la, lb = poisson_lambdas(elos[i], elos[j], TOTAL_GROUP, spread)
                gi = rng.poisson(la, n_sims); gj = rng.poisson(lb, n_sims)
            gf[:, i] += gi; ga[:, i] += gj; gf[:, j] += gj; ga[:, j] += gi
            pts[:, i] += np.where(gi > gj, 3, np.where(gi == gj, 1, 0))
            pts[:, j] += np.where(gj > gi, 3, np.where(gi == gj, 1, 0))
        gd = gf - ga
        # rank: primary pts, then gd, then gf, then random tiebreak
        rnd = rng.random((n_sims, 4))
        key = pts * 1e6 + gd * 1e3 + gf + rnd * 1e-3  # higher better
        order = np.argsort(-key, axis=1)  # (n_sims,4) local team positions by rank
        # map local 0..3 -> global team index
        gmap = np.array([tidx[t] for t in gteams])
        ranked_global = gmap[order]
        group_rank_team[g] = ranked_global
        win_idx[g] = ranked_global[:, 0]
        run_idx[g] = ranked_global[:, 1]
        third_idx[g] = ranked_global[:, 2]
        # stats of the 3rd-placed (by local pos = order[:,2])
        pos3 = order[:, 2]
        rows = np.arange(n_sims)
        third_stats[g] = (pts[rows, pos3], gd[rows, pos3], gf[rows, pos3],
                          rng.random(n_sims))

    # ---- BEST 8 THIRD-PLACE TEAMS ----
    glabels = list(D.GROUPS.keys())  # A..L
    # build score for each group's third
    third_score = np.zeros((n_sims, 12))
    for k, g in enumerate(glabels):
        p, d, f, r = third_stats[g]
        third_score[:, k] = p * 1e6 + d * 1e3 + f + r * 1e-3
    # top 8 groups (by third score) per sim
    top8_local = np.argsort(-third_score, axis=1)[:, :8]  # indices into glabels

    # ---- assemble R32 matchups per sim ----
    occ = {m: np.zeros(NT, dtype=np.int64) for m in range(73, 105)}
    pairs = {m: {} for m in range(73, 105)} if collect else None
    def _pair(mno, a, b):
        if pairs is None: return
        k = (a, b) if a < b else (b, a)
        pairs[mno][k] = pairs[mno].get(k, 0) + 1
    reach = {r: np.zeros(NT, dtype=np.int64) for r in
             ("R32", "R16", "QF", "SF", "FINAL", "WIN")}
    # group finish tallies
    finish = {g: {"win": np.zeros(NT, np.int64), "run": np.zeros(NT, np.int64),
                  "third_q": np.zeros(NT, np.int64), "out": np.zeros(NT, np.int64)}
              for g in glabels}
    # England-specific
    eng = tidx["England"]
    eng_records = {"win_L": 0, "run_L": 0, "third_L": 0, "out": 0}

    # pre-extract winner/runner/third arrays as (n_sims,) per group
    W = {g: win_idx[g] for g in glabels}
    R = {g: run_idx[g] for g in glabels}
    T3 = {g: third_idx[g] for g in glabels}

    # We must allocate Annex C per sim. Vectorize by grouping identical top8 sets.
    # Build a key per sim = sorted tuple of qualifying groups.
    top8_sets = [tuple(sorted(glabels[i] for i in row)) for row in top8_local]

    # finishing tallies
    for g in glabels:
        for s_team, bucket in ((W[g],"win"),(R[g],"run")):
            np.add.at(finish[g][bucket], s_team, 1)

    # Build third-qualified mask per group
    third_qual = {g: np.zeros(n_sims, dtype=bool) for g in glabels}
    for k, g in enumerate(glabels):
        # group g's third qualifies if k is in top8_local row
        third_qual[g] = (top8_local == k).any(axis=1)
    for g in glabels:
        np.add.at(finish[g]["third_q"], T3[g][third_qual[g]], 1)
        np.add.at(finish[g]["out"], T3[g][~third_qual[g]], 1)
        # 4th place always out
        np.add.at(finish[g]["out"], group_rank_team[g][:,3], 1)

    # England group finish
    eng_records["win_L"]  = int((W["L"] == eng).sum())
    eng_records["run_L"]  = int((R["L"] == eng).sum())
    eng_records["third_L"]= int(((T3["L"] == eng) & third_qual["L"]).sum())
    eng_records["out"]    = n_sims - eng_records["win_L"] - eng_records["run_L"] - eng_records["third_L"]

    # ---- iterate sims for knockout (python loop; vectorization of bracket is messy) ----
    # Precompute per-sim arrays accessed by index s.
    Wg = {g: W[g] for g in glabels}; Rg = {g: R[g] for g in glabels}; Tg = {g: T3[g] for g in glabels}

    def ko_winner(a, b, s_elo_a, s_elo_b, rng2):
        la, lb = poisson_lambdas(s_elo_a, s_elo_b, TOTAL_KO, spread)
        ga = rng2.poisson(la); gb = rng2.poisson(lb)
        if ga > gb: return a
        if gb > ga: return b
        # ET/pens via Elo logistic
        p = 1.0 / (1.0 + 10 ** (-(s_elo_a - s_elo_b) / 400.0))
        return a if rng2.random() < p else b

    elo_arr = ratings

    # localize for speed
    rngp = rng.poisson; rngr = rng.random
    for s in range(n_sims):
        thirds_set = top8_sets[s]
        assign = ANNEXC.get(frozenset(thirds_set))
        # third team for each winner-vs-third match
        third_for_winner = {}  # winner-group -> third-group letter
        # assign order corresponds to slots [1A,1B,1D,1E,1G,1I,1K,1L]
        slot_groups = ["A","B","D","E","G","I","K","L"]
        for col, wg in enumerate(slot_groups):
            third_for_winner[wg] = assign[col]

        # resolve all 32 knockout matches
        res = {}
        # R32
        for (mno, sa, sb, pool) in D.R32:
            ta = _slot_team(sa, s, Wg, Rg)
            if sb == "3rd":
                wgroup = D.R32_THIRD_WINNER[mno]
                tg = third_for_winner[wgroup]
                tb = Tg[tg][s]
            else:
                tb = _slot_team(sb, s, Wg, Rg)
            occ[mno][ta] += 1; occ[mno][tb] += 1; _pair(mno, ta, tb)
            reach["R32"][ta] += 1; reach["R32"][tb] += 1
            w = ko_winner(ta, tb, elo_arr[ta], elo_arr[tb], rng)
            res[mno] = w
        # R16
        for mno, (f1, f2) in D.R16.items():
            ta, tb = res[f1], res[f2]
            occ[mno][ta] += 1; occ[mno][tb] += 1; _pair(mno, ta, tb)
            reach["R16"][ta] += 1; reach["R16"][tb] += 1
            res[mno] = ko_winner(ta, tb, elo_arr[ta], elo_arr[tb], rng)
        # QF
        for mno, (f1, f2) in D.QF.items():
            ta, tb = res[f1], res[f2]
            occ[mno][ta] += 1; occ[mno][tb] += 1; _pair(mno, ta, tb)
            reach["QF"][ta] += 1; reach["QF"][tb] += 1
            res[mno] = ko_winner(ta, tb, elo_arr[ta], elo_arr[tb], rng)
        # SF
        for mno, (f1, f2) in D.SF.items():
            ta, tb = res[f1], res[f2]
            occ[mno][ta] += 1; occ[mno][tb] += 1; _pair(mno, ta, tb)
            reach["SF"][ta] += 1; reach["SF"][tb] += 1
            res[mno] = ko_winner(ta, tb, elo_arr[ta], elo_arr[tb], rng)
        # Final + third place
        fa, fb = res[101], res[102]
        occ[104][fa] += 1; occ[104][fb] += 1; _pair(104, fa, fb)
        reach["FINAL"][fa] += 1; reach["FINAL"][fb] += 1
        champ = ko_winner(fa, fb, elo_arr[fa], elo_arr[fb], rng)
        reach["WIN"][champ] += 1

    return {"occ": occ, "reach": reach, "finish": finish, "pairs": pairs,
            "eng_records": eng_records, "n_sims": n_sims, "teams": teams, "tidx": tidx}

def _slot_team(slot, s, Wg, Rg):
    typ = slot[0]; g = slot[1]
    return Wg[g][s] if typ == "1" else Rg[g][s]

# ---------------------------------------------------------------------------
def title_probs_from(reach, teams, n):
    return {teams[i]: reach["WIN"][i] / n for i in range(len(teams))}

def fit_ratings(spread=1.0, iters=12, fit_sims=8000, seed=42, verbose=True):
    """Iteratively nudge each market team's effective Elo so the simulated
    title probability matches its betting-market title odds. Non-market teams
    keep their Elo. This anchors the model on the betting market (per brief)
    while Elo discriminates the rest of the 48-team field."""
    teams = D.ALL_TEAMS
    tidx = {t: i for i, t in enumerate(teams)}
    ratings = base_ratings()
    market = D.MARKET_TITLE_PROB
    fit_teams = list(market.keys())
    for it in range(iters):
        out = simulate(fit_sims, spread, np.random.default_rng(seed + it), ratings=ratings.copy())
        tp = title_probs_from(out["reach"], out["teams"], out["n_sims"])
        step = 130.0 * (0.8 ** it) + 25.0   # decaying learning rate (Elo pts)
        for t in fit_teams:
            pm = max(tp.get(t, 0.0), 1e-4)
            adj = np.log(market[t] / pm)
            ratings[tidx[t]] += np.clip(step * adj, -120, 120)
        if verbose:
            sse = sum((tp.get(t,0)-market[t])**2 for t in fit_teams)
            print(f" iter {it:2d} step={step:5.1f} sse={sse:.5f}")
    return ratings

if __name__ == "__main__":
    r = fit_ratings()
    out = simulate(20000, 1.0, np.random.default_rng(99), ratings=r)
    tp = title_probs_from(out["reach"], out["teams"], out["n_sims"])
    print("\nFitted title probabilities vs market:")
    for t in sorted(D.MARKET_TITLE_PROB, key=lambda x:-D.MARKET_TITLE_PROB[x]):
        print(f"  {t:12s} market {D.MARKET_TITLE_PROB[t]*100:4.1f}%  model {tp.get(t,0)*100:4.1f}%")
    print("\nTop-20 effective ratings:")
    order = np.argsort(-r)
    for i in order[:20]:
        print(f"  {out['teams'][i]:14s} {r[i]:6.0f}")

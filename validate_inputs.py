#!/usr/bin/env python3
"""Validate the live data inputs without running the model.

Checks results_log.json, odds.json, and match_odds.json: that they parse as JSON,
have the right shape, and use the exact team names from data.py. Canonical team
names are read from data.py STATICALLY via `ast` — data.py (and build.py/model.py)
are never imported or executed, so this is safe to run on untrusted pull requests.

Run locally before opening a PR:
    python3 validate_inputs.py
Exits non-zero (with a list of errors) if anything is wrong.

Inspect the data shape (GROUPS / GROUP_FIXTURES / JSON inputs) without running
the model — a safe, allowlistable replacement for ad-hoc `python3 -c` snippets:
    python3 validate_inputs.py --describe
"""
import ast, json, os, sys, difflib, datetime
import schedule_gate as SG

HERE = os.path.dirname(os.path.abspath(__file__))
errors, warnings = [], []
def err(m): errors.append(m)
def warn(m): warnings.append(m)

def canonical_teams():
    """Extract team names + group from data.py's GROUPS literal WITHOUT executing
    the module. ast.literal_eval only evaluates literals (no function calls), so a
    malicious data.py cannot run code through this path. Handles both a plain
    assignment and an annotated one (GROUPS: dict = {...})."""
    src = open(os.path.join(HERE, "data.py"), encoding="utf-8").read()
    value = None
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "GROUPS" for t in node.targets):
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.target.id == "GROUPS":
            value = node.value
    if value is None:
        sys.exit("ERROR: could not find a GROUPS assignment in data.py")
    try:
        groups = ast.literal_eval(value)
    except (ValueError, TypeError):
        sys.exit("ERROR: GROUPS in data.py is not a plain literal dict the validator can read statically")
    teams = {t for ts in groups.values() for t in ts}
    group_of = {t: g for g, ts in groups.items() for t in ts}
    return teams, group_of

def hint(name, teams):
    m = difflib.get_close_matches(str(name), teams, n=1)
    return f' (did you mean "{m[0]}"?)' if m else ""

def load_json(name):
    path = os.path.join(HERE, name)
    if not os.path.exists(path):
        return None  # all three inputs are optional
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception as e:
        err(f"{name}: invalid JSON — {e}")
        return None

def check_team(tag, name, teams):
    if name is not None and name not in teams:
        err(f'{tag}: unknown team "{name}"{hint(name, teams)}')

def is_num(v):  # reject bools, which are ints in Python
    return isinstance(v, (int, float)) and not isinstance(v, bool)

def goal_ok(v):  # build.py does int(v), so accept ints and whole-number floats
    return is_num(v) and v >= 0 and float(v).is_integer()

def check_fixture(tag, e, teams, group_of, seen):
    """Shared h/a checks for a results/odds line: known teams, not self, not a dup."""
    check_team(tag, e.get("h"), teams); check_team(tag, e.get("a"), teams)
    h, a = e.get("h"), e.get("a")
    if h is not None and h == a:
        err(f'{tag}: "h" and "a" are the same team ("{h}") — not a valid fixture')
    if h in teams and a in teams and h != a:
        key = frozenset((h, a))
        if key in seen:
            warn(f"{tag}: duplicate game {h} vs {a} — build.py keeps one and ignores the rest")
        seen.add(key)
    return h, a

def static_value(name):
    """ast.literal_eval of a top-level `name = <literal>` (or annotated) assignment
    in data.py, WITHOUT importing/executing it — same safety property as
    canonical_teams(). Returns None if absent or not a plain literal."""
    src = open(os.path.join(HERE, "data.py"), encoding="utf-8").read()
    value = None
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets):
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.target.id == name:
            value = node.value
    if value is None:
        return None
    try:
        return ast.literal_eval(value)
    except (ValueError, TypeError):
        return None

def describe():
    """Print the structure of the data inputs (static read of data.py — never
    imported). Allowlistable single command, so the automated routine can inspect
    inputs without emitting an ad-hoc multi-line `python3 -c "..."` (a newline + #
    inside such a snippet trips the command-safety guard and stalls unattended runs)."""
    groups = static_value("GROUPS")
    if isinstance(groups, dict):
        print(f"GROUPS: {len(groups)} groups, "
              f"{sum(len(v) for v in groups.values())} teams")
        for g, ts in groups.items():
            print(f"  {g}: {', '.join(ts)}")
    else:
        print("GROUPS: <not a literal the validator can read statically>")

    fixtures = static_value("GROUP_FIXTURES")
    if isinstance(fixtures, list):
        print(f"\nGROUP_FIXTURES: {len(fixtures)} fixtures "
              f"(home, away, group, date, time, city)")
        if fixtures:
            print(f"  e.g. {fixtures[0]}")
    else:
        print("\nGROUP_FIXTURES: <not a literal the validator can read statically>")

    print("\nLive JSON inputs:")
    for name in ("results_log.json", "odds.json", "match_odds.json", "ko_results.json"):
        data = load_json(name)
        if data is None:
            print(f"  {name}: (absent)")
        elif isinstance(data, list):
            print(f"  {name}: array, {len(data)} entries")
        elif isinstance(data, dict):
            print(f"  {name}: object, {len(data)} keys")
        else:
            print(f"  {name}: {type(data).__name__}")

def main():
    teams, group_of = canonical_teams()

    # Deterministic kickoff-time gate inputs: the schedule, read statically (never
    # executing data.py), and the real current time. A result for a fixture that
    # cannot have finished yet is a fabrication and is rejected here, before
    # publish.sh can commit it.
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    gf = static_value("GROUP_FIXTURES")
    group_kos = SG.group_fixture_kickoffs(gf) if isinstance(gf, list) else {}

    rl = load_json("results_log.json")
    if isinstance(rl, list):
        seen = set()
        for i, e in enumerate(rl):
            tag = f"results_log.json[{i}]"
            if not isinstance(e, dict):
                err(f"{tag}: must be an object {{h,a,hg,ag}}"); continue
            for k in ("h", "a", "hg", "ag"):
                if k not in e: err(f'{tag}: missing "{k}"')
            h, a = check_fixture(tag, e, teams, group_of, seen)
            for k in ("hg", "ag"):
                v = e.get(k)
                if v is not None and not goal_ok(v):
                    err(f'{tag}: "{k}" must be a non-negative whole number (got {v!r})')
            if h in teams and a in teams and h != a:
                ok, reason = SG.result_admissible(h, a, group_of, group_kos, now_utc)
                if not ok:
                    err(f"{tag}: {reason}")
    elif rl is not None:
        err("results_log.json: must be a JSON array")

    od = load_json("odds.json")
    if isinstance(od, dict):
        for team, v in od.items():
            check_team("odds.json", team, teams)
            if not is_num(v):
                err(f'odds.json: "{team}" probability must be a number (got {v!r})')
            elif not (0 < v < 1):
                warn(f'odds.json: "{team}" = {v} is outside (0,1) and will be ignored by the model')
    elif od is not None:
        err('odds.json: must be a JSON object {"Team": probability}')

    mo = load_json("match_odds.json")
    if isinstance(mo, list):
        seen = set()
        for i, e in enumerate(mo):
            tag = f"match_odds.json[{i}]"
            if not isinstance(e, dict):
                err(f"{tag}: must be an object {{h,a,home,draw,away}}"); continue
            for k in ("h", "a", "home", "draw", "away"):
                if k not in e: err(f'{tag}: missing "{k}"')
            h, a = check_fixture(tag, e, teams, group_of, seen)
            if h in teams and a in teams and h != a and group_of.get(h) != group_of.get(a):
                warn(f"{tag}: {h} and {a} are in different groups — the model only "
                     f"prices same-group games, so this line will be ignored")
            for k in ("home", "draw", "away"):
                v = e.get(k)
                if v is not None and (not is_num(v) or v <= 0):
                    err(f'{tag}: "{k}" must be a positive number (got {v!r})')
    elif mo is not None:
        err("match_odds.json: must be a JSON array")

    # ko_results.json — played knockout results, keyed by match number. Gated on the
    # knockout match's scheduled kickoff (the KO analog of the group kickoff gate), so
    # a premature/fabricated late-round score errors here before publish.sh can commit.
    kor = load_json("ko_results.json")
    if isinstance(kor, list):
        ki = static_value("KO_INFO")
        ko_kos = SG.knockout_kickoffs(ki) if isinstance(ki, dict) else {}
        seen_mno = set()
        for i, e in enumerate(kor):
            tag = f"ko_results.json[{i}]"
            if not isinstance(e, dict):
                err(f"{tag}: must be an object {{match_no, winner, ...}}"); continue
            for k in ("match_no", "winner"):
                if k not in e: err(f'{tag}: missing "{k}"')
            mno = e.get("match_no")
            # 73–104 are the knockout matches; 103 (third-place playoff) is excluded —
            # the model never simulates or holds it fixed, so it must not be ingested.
            valid_mno = (isinstance(mno, int) and not isinstance(mno, bool)
                         and 73 <= mno <= 104 and mno != 103)
            if mno is not None and not valid_mno:
                err(f'{tag}: "match_no" must be an integer in 73–104 (excluding 103, the '
                    f"unmodeled third-place playoff) (got {mno!r})")
            if valid_mno:
                if mno in seen_mno:
                    warn(f"{tag}: duplicate match_no {mno} — build.py keeps the first")
                seen_mno.add(mno)
            check_team(tag, e.get("winner"), teams)
            for side in ("h", "a"):       # optional, but validated if present
                if e.get(side) is not None:
                    check_team(tag, e.get(side), teams)
            for k in ("hg", "ag"):
                v = e.get(k)
                if v is not None and not goal_ok(v):
                    err(f'{tag}: "{k}" must be a non-negative whole number (got {v!r})')
            if valid_mno:
                ok, reason = SG.ko_result_admissible(mno, ko_kos, now_utc)
                if not ok:
                    err(f"{tag}: {reason}")
    elif kor is not None:
        err("ko_results.json: must be a JSON array")

    for w in warnings:
        print(f"warning: {w}")
    if errors:
        print()
        for e in errors:
            print(f"error: {e}")
        print(f"\n❌ {len(errors)} error(s) in the data inputs — see above.")
        sys.exit(1)
    print(f"✅ Data inputs valid against {len(teams)} known teams"
          + (f" ({len(warnings)} warning(s))." if warnings else "."))

if __name__ == "__main__":
    if "--describe" in sys.argv[1:]:
        describe()
    else:
        main()

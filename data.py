"""
2026 FIFA World Cup — static tournament data.
Sources (all accessed 14-15 June 2026):
  - Groups / fixtures / venues: Fox Sports official broadcast schedule, CBS Sports.
  - Knockout slot structure + Annex C: Wikipedia "2026 FIFA World Cup knockout stage" (FIFA regs).
  - Knockout venues/dates per match number: Fox Sports (match numbers in URLs).
  - Elo ratings: worldfootballrankings.com (eloratings.net-derived), as of 15 June 2026.
  - Market title odds: Kalshi via Covers.com, as of 13 June 2026 (top-of-market calibration anchor).
All kickoff times Eastern (ET).
"""

# ---------------------------------------------------------------------------
# GROUPS
# ---------------------------------------------------------------------------
GROUPS = {
    "A": ["Mexico", "South Africa", "South Korea", "Czechia"],
    "B": ["Canada", "Bosnia & Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["USA", "Paraguay", "Australia", "Türkiye"],
    "E": ["Germany", "Curaçao", "Côte d'Ivoire", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

# ---------------------------------------------------------------------------
# ELO RATINGS (worldfootballrankings.com / eloratings.net scale, 15 Jun 2026)
# Values marked APPROX were not directly listed on the source's top-50 view and
# are estimated on the same scale from FIFA ranking / confederation peers. They
# are all lower-tier sides whose exact rating barely moves the knockout picture;
# the nightly updater can refine them. Confirmed values carry no note.
# ---------------------------------------------------------------------------
ELO = {
    # Confirmed from source table
    "Argentina": 1877, "Spain": 1875, "France": 1871, "England": 1828,
    "Portugal": 1768, "Brazil": 1765, "Morocco": 1756, "Netherlands": 1749,
    "Germany": 1744, "Belgium": 1742, "Croatia": 1715, "Mexico": 1701,
    "Colombia": 1698, "USA": 1689, "Senegal": 1684, "Uruguay": 1673,
    "Japan": 1666, "Switzerland": 1641, "Iran": 1620, "South Korea": 1613,
    "Australia": 1606, "Austria": 1597, "Türkiye": 1579, "Algeria": 1571,
    "Ecuador": 1571, "Côte d'Ivoire": 1569, "Egypt": 1562, "Norway": 1557,
    "Canada": 1552, "Panama": 1539, "Sweden": 1533, "Scotland": 1519,
    "Paraguay": 1488, "Czechia": 1485, "DR Congo": 1474, "Qatar": 1459,
    "Uzbekistan": 1459,
    # APPROX (lower-tier, not in source top-50 view)
    "Saudi Arabia": 1450,        # APPROX
    "Tunisia": 1445,             # APPROX
    "South Africa": 1440,        # APPROX
    "Ghana": 1440,               # APPROX
    "Bosnia & Herzegovina": 1500,# APPROX
    "Iraq": 1410,                # APPROX
    "Cape Verde": 1400,          # APPROX
    "Jordan": 1375,              # APPROX
    "New Zealand": 1276,         # confirmed (OFC best on source)
    "Curaçao": 1330,             # APPROX
    "Haiti": 1320,               # APPROX
}

# Host nations (modest home advantage applied in knockout/group neutral-ish venues)
HOSTS = {"USA", "Mexico", "Canada"}

# ---------------------------------------------------------------------------
# MARKET TITLE ODDS — implied win probability (Kalshi via Covers, 13 Jun 2026)
# Used ONLY to calibrate the rating spread so simulated title odds match market.
# ---------------------------------------------------------------------------
MARKET_TITLE_PROB = {
    "France": 0.172, "Spain": 0.170, "Portugal": 0.110, "England": 0.108,
    "Argentina": 0.089, "Brazil": 0.085, "Netherlands": 0.058, "Germany": 0.051,
    "USA": 0.035, "Norway": 0.023, "Belgium": 0.021, "Mexico": 0.020,
    "Colombia": 0.017, "Japan": 0.017, "Morocco": 0.015,
}

# ---------------------------------------------------------------------------
# MARKET PER-GAME 1X2 ODDS (second calibration input). Populated from
# match_odds.json at build time: frozenset({home,away}) -> {h,a,home,draw,away}
# (implied win/draw/loss probabilities, de-vigged in the model). A scheduled but
# unplayed group game with a market line is priced directly off it, bypassing the
# Elo gap; every other game still uses Elo + the title-odds calibration.
# ---------------------------------------------------------------------------
MATCH_ODDS = {}

# ---------------------------------------------------------------------------
# COMPLETED KNOCKOUT RESULTS — {match_no: winner_team_name}. Populated from
# ko_results.json at build time. Empty by default: no knockout result is ever
# committed here. They enter ONLY through the cross-validated, kickoff-gated
# fetch_results.py path (mirroring the group-stage no-fabrication boundary). A
# played knockout match is then held FIXED across every simulation (model.simulate),
# so the whole bracket stays consistent with reality, and its winner is emitted on
# the match object for the dashboard's pick'em "you vs the model" scoring.
# ---------------------------------------------------------------------------
KO_RESULTS = {}

# ---------------------------------------------------------------------------
# COMPLETED RESULTS (as of ~8pm ET, 14 Jun 2026). (home, away, hg, ag)
# Côte d'Ivoire 1-0 Ecuador and Australia 1-0 Türkiye inferred from Elo deltas;
# scorelines for those two are placeholders pending confirmation (result/winner
# is firm; exact goals only affect goal-difference tiebreakers marginally).
# ---------------------------------------------------------------------------
RESULTS = [
    # Group A
    ("Mexico", "South Africa", 2, 0),
    ("South Korea", "Czechia", 2, 1),
    # Group B
    ("Canada", "Bosnia & Herzegovina", 1, 1),
    ("Qatar", "Switzerland", 1, 1),
    # Group C
    ("Brazil", "Morocco", 1, 1),
    ("Scotland", "Haiti", 1, 0),
    # Group D
    ("USA", "Paraguay", 4, 1),
    ("Australia", "Türkiye", 2, 0),   # confirmed (ESPN/FIFA)
    # Group E
    ("Germany", "Curaçao", 7, 1),
    ("Côte d'Ivoire", "Ecuador", 1, 0),  # confirmed (Amad Diallo 90', ESPN)
    # Group F
    ("Netherlands", "Japan", 2, 2),
    ("Sweden", "Tunisia", 5, 1),
]

# ---------------------------------------------------------------------------
# REMAINING GROUP FIXTURES (home, away, group, "Mon DD", "h:mm ap ET", City)
# From Fox Sports official schedule. Used to simulate the rest of the group stage.
# ---------------------------------------------------------------------------
GROUP_FIXTURES = [
    # Jun 15
    ("Spain", "Cape Verde", "H", "Jun 15", "12:00 PM", "Atlanta"),
    ("Belgium", "Egypt", "G", "Jun 15", "3:00 PM", "Seattle"),
    ("Saudi Arabia", "Uruguay", "H", "Jun 15", "6:00 PM", "Miami"),
    ("Iran", "New Zealand", "G", "Jun 15", "9:00 PM", "Los Angeles"),
    # Jun 16
    ("France", "Senegal", "I", "Jun 16", "3:00 PM", "New York/NJ"),
    ("Iraq", "Norway", "I", "Jun 16", "6:00 PM", "Boston"),
    ("Argentina", "Algeria", "J", "Jun 16", "9:00 PM", "Kansas City"),
    ("Austria", "Jordan", "J", "Jun 16", "12:00 AM", "San Francisco"),
    # Jun 17
    ("Portugal", "DR Congo", "K", "Jun 17", "1:00 PM", "Houston"),
    ("England", "Croatia", "L", "Jun 17", "4:00 PM", "Dallas"),
    ("Ghana", "Panama", "L", "Jun 17", "7:00 PM", "Toronto"),
    ("Uzbekistan", "Colombia", "K", "Jun 17", "10:00 PM", "Mexico City"),
    # Jun 18
    ("Czechia", "South Africa", "A", "Jun 18", "12:00 PM", "Atlanta"),
    ("Switzerland", "Bosnia & Herzegovina", "B", "Jun 18", "3:00 PM", "Los Angeles"),
    ("Canada", "Qatar", "B", "Jun 18", "6:00 PM", "Vancouver"),
    ("Mexico", "South Korea", "A", "Jun 18", "9:00 PM", "Guadalajara"),
    # Jun 19
    ("USA", "Australia", "D", "Jun 19", "3:00 PM", "Seattle"),
    ("Scotland", "Morocco", "C", "Jun 19", "3:00 PM", "Boston"),
    ("Brazil", "Haiti", "C", "Jun 19", "9:00 PM", "Philadelphia"),
    ("Türkiye", "Paraguay", "D", "Jun 19", "12:00 AM", "San Francisco"),
    # Jun 20
    ("Netherlands", "Sweden", "F", "Jun 20", "1:00 PM", "Houston"),
    ("Germany", "Côte d'Ivoire", "E", "Jun 20", "4:00 PM", "Toronto"),
    ("Ecuador", "Curaçao", "E", "Jun 20", "8:00 PM", "Kansas City"),
    ("Tunisia", "Japan", "F", "Jun 20", "12:00 AM", "Monterrey"),
    # Jun 21
    ("Spain", "Saudi Arabia", "H", "Jun 21", "12:00 PM", "Atlanta"),
    ("Belgium", "Iran", "G", "Jun 21", "3:00 PM", "Los Angeles"),
    ("Uruguay", "Cape Verde", "H", "Jun 21", "6:00 PM", "Miami"),
    ("New Zealand", "Egypt", "G", "Jun 21", "9:00 PM", "Vancouver"),
    # Jun 22
    ("Argentina", "Austria", "J", "Jun 22", "1:00 PM", "Dallas"),
    ("France", "Iraq", "I", "Jun 22", "5:00 PM", "Philadelphia"),
    ("Norway", "Senegal", "I", "Jun 22", "8:00 PM", "New York/NJ"),
    ("Jordan", "Algeria", "J", "Jun 22", "11:00 PM", "San Francisco"),
    # Jun 23
    ("Portugal", "Uzbekistan", "K", "Jun 23", "1:00 PM", "Houston"),
    ("England", "Ghana", "L", "Jun 23", "4:00 PM", "Boston"),
    ("Panama", "Croatia", "L", "Jun 23", "7:00 PM", "Toronto"),
    ("Colombia", "DR Congo", "K", "Jun 23", "10:00 PM", "Guadalajara"),
    # Jun 24
    ("Switzerland", "Canada", "B", "Jun 24", "3:00 PM", "Vancouver"),
    ("Bosnia & Herzegovina", "Qatar", "B", "Jun 24", "3:00 PM", "Seattle"),
    ("Brazil", "Scotland", "C", "Jun 24", "6:00 PM", "Miami"),
    ("Morocco", "Haiti", "C", "Jun 24", "6:00 PM", "Atlanta"),
    ("Mexico", "Czechia", "A", "Jun 24", "9:00 PM", "Mexico City"),
    ("South Korea", "South Africa", "A", "Jun 24", "9:00 PM", "Monterrey"),
    # Jun 25
    ("Ecuador", "Germany", "E", "Jun 25", "4:00 PM", "New York/NJ"),
    ("Curaçao", "Côte d'Ivoire", "E", "Jun 25", "4:00 PM", "Philadelphia"),
    ("Tunisia", "Netherlands", "F", "Jun 25", "7:00 PM", "Kansas City"),
    ("Japan", "Sweden", "F", "Jun 25", "7:00 PM", "Dallas"),
    ("USA", "Türkiye", "D", "Jun 25", "10:00 PM", "Los Angeles"),
    ("Paraguay", "Australia", "D", "Jun 25", "10:00 PM", "San Francisco"),
    # Jun 26
    ("Norway", "France", "I", "Jun 26", "3:00 PM", "Boston"),
    ("Senegal", "Iraq", "I", "Jun 26", "3:00 PM", "Toronto"),
    ("Uruguay", "Spain", "H", "Jun 26", "8:00 PM", "Guadalajara"),
    ("Cape Verde", "Saudi Arabia", "H", "Jun 26", "8:00 PM", "Houston"),
    ("New Zealand", "Belgium", "G", "Jun 26", "11:00 PM", "Vancouver"),
    ("Egypt", "Iran", "G", "Jun 26", "11:00 PM", "Seattle"),
    # Jun 27
    ("Panama", "England", "L", "Jun 27", "5:00 PM", "New York/NJ"),
    ("Croatia", "Ghana", "L", "Jun 27", "5:00 PM", "Philadelphia"),
    ("Colombia", "Portugal", "K", "Jun 27", "7:30 PM", "Miami"),
    ("DR Congo", "Uzbekistan", "K", "Jun 27", "7:30 PM", "Atlanta"),
    ("Argentina", "Jordan", "J", "Jun 27", "10:00 PM", "Dallas"),
    ("Algeria", "Austria", "J", "Jun 27", "10:00 PM", "Kansas City"),
]

# ---------------------------------------------------------------------------
# KNOCKOUT STRUCTURE
# Each R32 match: (match_no, slotA, slotB). Slots:
#   "1X" group winner, "2X" runner-up, "3[set]" best-third from a pool of groups.
# 3rd-place pools per Wikipedia/FIFA regs (authoritative for allocation).
# ---------------------------------------------------------------------------

R32 = [
    # match_no, slotA, slotB, pool(for the 3rd slot or None)
    (73, "2A", "2B", None),
    (74, "1E", "3rd", "ABCDF"),
    (75, "1F", "2C", None),
    (76, "1C", "2F", None),
    (77, "1I", "3rd", "CDFGH"),
    (78, "2E", "2I", None),
    (79, "1A", "3rd", "CEFHI"),
    (80, "1L", "3rd", "EHIJK"),
    (81, "1D", "3rd", "BEFIJ"),
    (82, "1G", "3rd", "AEHIJ"),
    (83, "2K", "2L", None),
    (84, "1H", "2J", None),
    (85, "1B", "3rd", "EFGIJ"),
    (86, "1J", "2H", None),
    (87, "1K", "3rd", "DEIJL"),
    (88, "2D", "2G", None),
]

# Which group winner each "3rd" slot belongs to (for Annex C column lookup)
R32_THIRD_WINNER = {74: "E", 77: "I", 79: "A", 80: "L", 81: "D", 82: "G", 85: "B", 87: "K"}

# Round of 16 / QF / SF / Final pairings: match_no -> (feeder1, feeder2)
R16 = {89: (74, 77), 90: (73, 75), 91: (76, 78), 92: (79, 80),
       93: (83, 84), 94: (81, 82), 95: (86, 88), 96: (85, 87)}
QF = {97: (89, 90), 98: (93, 94), 99: (91, 92), 100: (95, 96)}
SF = {101: (97, 98), 102: (99, 100)}
FINAL = {104: (101, 102)}

# ---------------------------------------------------------------------------
# KNOCKOUT VENUE / DATE / KO TIME per match number (Fox Sports official).
# ---------------------------------------------------------------------------
KO_INFO = {
    73: ("Los Angeles", "Jun 28", "3:00 PM"),
    74: ("Boston", "Jun 29", "4:30 PM"),
    75: ("Monterrey", "Jun 29", "9:00 PM"),
    76: ("Houston", "Jun 29", "1:00 PM"),
    77: ("New York/NJ", "Jun 30", "5:00 PM"),
    78: ("Dallas", "Jun 30", "1:00 PM"),
    79: ("Mexico City", "Jun 30", "9:00 PM"),
    80: ("Atlanta", "Jul 1", "12:00 PM"),
    81: ("San Francisco", "Jul 1", "8:00 PM"),
    82: ("Seattle", "Jul 1", "4:00 PM"),
    83: ("Toronto", "Jul 2", "7:00 PM"),
    84: ("Los Angeles", "Jul 2", "3:00 PM"),
    85: ("Vancouver", "Jul 2", "11:00 PM"),
    86: ("Miami", "Jul 3", "6:00 PM"),
    87: ("Kansas City", "Jul 3", "9:30 PM"),
    88: ("Dallas", "Jul 3", "2:00 PM"),
    89: ("Philadelphia", "Jul 4", "5:00 PM"),
    90: ("Houston", "Jul 4", "1:00 PM"),
    91: ("New York/NJ", "Jul 5", "4:00 PM"),
    92: ("Mexico City", "Jul 5", "8:00 PM"),
    93: ("Dallas", "Jul 6", "3:00 PM"),
    94: ("Seattle", "Jul 6", "8:00 PM"),
    95: ("Atlanta", "Jul 7", "12:00 PM"),
    96: ("Vancouver", "Jul 7", "4:00 PM"),
    97: ("Boston", "Jul 9", "4:00 PM"),
    98: ("Los Angeles", "Jul 10", "3:00 PM"),
    99: ("Miami", "Jul 11", "5:00 PM"),
    100: ("Kansas City", "Jul 11", "9:00 PM"),
    101: ("Dallas", "Jul 14", "3:00 PM"),
    102: ("Atlanta", "Jul 15", "3:00 PM"),
    103: ("Miami", "Jul 18", "5:00 PM"),
    104: ("New York/NJ", "Jul 19", "3:00 PM"),
}

ROUND_NAME = {}
for m in range(73, 89): ROUND_NAME[m] = "Round of 32"
for m in range(89, 97): ROUND_NAME[m] = "Round of 16"
for m in range(97, 101): ROUND_NAME[m] = "Quarterfinal"
for m in (101, 102): ROUND_NAME[m] = "Semifinal"
ROUND_NAME[103] = "Third-place"
ROUND_NAME[104] = "Final"

TEAM_GROUP = {t: g for g, ts in GROUPS.items() for t in ts}
ALL_TEAMS = list(TEAM_GROUP.keys())

"""Seed script for the IPL sample database.

Creates backend/databases/ipl.db from scratch (drops and recreates).
Uses Faker(seed=42) + random.seed(42) for full reproducibility.

Tables:
  teams              — IPL franchises (10 real-feeling franchises)
  venues             — cricket grounds with capacity
  players            — ~150 players with role / batting / bowling style
  seasons            — 2020-2024 (5 seasons)
  matches            — ~70 matches per season (~350 total), FK→teams/venues/seasons
  match_squads       — 11 players per team per match (~15,400 rows)
  innings_scorecards — batting line per batter per innings (~3,900 rows)
  bowling_figures    — bowling line per bowler per innings (~2,800 rows)

Run:
    cd backend
    .venv/Scripts/python.exe databases/seed_ipl.py
"""

from __future__ import annotations

import os
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

# ---------------------------------------------------------------------------
# Deterministic seeds
# ---------------------------------------------------------------------------
Faker.seed(42)
random.seed(42)
fake = Faker()

# ---------------------------------------------------------------------------
# Output path
# ---------------------------------------------------------------------------
DB_PATH = Path(__file__).resolve().parent / "ipl.db"

# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------
DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS teams (
    team_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    short_name      TEXT    NOT NULL UNIQUE,   -- e.g. MI, CSK, RCB
    city            TEXT    NOT NULL,
    home_venue      TEXT    NOT NULL,
    founded_year    INTEGER NOT NULL,
    titles          INTEGER NOT NULL DEFAULT 0 -- IPL titles won (historical)
);

CREATE TABLE IF NOT EXISTS venues (
    venue_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    city            TEXT    NOT NULL,
    capacity        INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS players (
    player_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    country         TEXT    NOT NULL,
    role            TEXT    NOT NULL,   -- batter | bowler | all-rounder | wicketkeeper
    batting_style   TEXT    NOT NULL,   -- right-hand | left-hand
    bowling_style   TEXT    NOT NULL,   -- right-arm fast | left-arm fast | right-arm medium
                                        -- left-arm medium | right-arm off-spin | left-arm spin
                                        -- right-arm leg-spin | none
    date_of_birth   DATE    NOT NULL,
    is_overseas     INTEGER NOT NULL DEFAULT 0  -- 0=Indian, 1=overseas
);

CREATE TABLE IF NOT EXISTS seasons (
    season_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    year            INTEGER NOT NULL UNIQUE,
    winning_team_id INTEGER             REFERENCES teams(team_id),
    runner_up_id    INTEGER             REFERENCES teams(team_id),
    final_venue_id  INTEGER             REFERENCES venues(venue_id),
    total_matches   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS matches (
    match_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id           INTEGER NOT NULL REFERENCES seasons(season_id),
    match_date          DATE    NOT NULL,
    team_a_id           INTEGER NOT NULL REFERENCES teams(team_id),
    team_b_id           INTEGER NOT NULL REFERENCES teams(team_id),
    venue_id            INTEGER NOT NULL REFERENCES venues(venue_id),
    toss_winner_id      INTEGER NOT NULL REFERENCES teams(team_id),
    toss_decision       TEXT    NOT NULL,   -- bat | field
    winner_id           INTEGER             REFERENCES teams(team_id),  -- NULL = no result/tie
    win_margin_runs     INTEGER,            -- set when team batting first wins
    win_margin_wickets  INTEGER,            -- set when team batting second wins
    is_playoff          INTEGER NOT NULL DEFAULT 0,  -- 0=league, 1=playoff
    match_type          TEXT    NOT NULL DEFAULT 'league'  -- league | qualifier1 | eliminator | qualifier2 | final
);

CREATE TABLE IF NOT EXISTS match_squads (
    squad_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id    INTEGER NOT NULL REFERENCES matches(match_id),
    player_id   INTEGER NOT NULL REFERENCES players(player_id),
    team_id     INTEGER NOT NULL REFERENCES teams(team_id),
    is_captain  INTEGER NOT NULL DEFAULT 0,
    is_keeper   INTEGER NOT NULL DEFAULT 0,
    UNIQUE(match_id, player_id)
);

CREATE TABLE IF NOT EXISTS innings_scorecards (
    scorecard_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id        INTEGER NOT NULL REFERENCES matches(match_id),
    batting_team_id INTEGER NOT NULL REFERENCES teams(team_id),
    innings_number  INTEGER NOT NULL,   -- 1 or 2
    batter_id       INTEGER NOT NULL REFERENCES players(player_id),
    batting_order   INTEGER NOT NULL,   -- 1-11
    runs            INTEGER NOT NULL DEFAULT 0,
    balls_faced     INTEGER NOT NULL DEFAULT 0,
    fours           INTEGER NOT NULL DEFAULT 0,
    sixes           INTEGER NOT NULL DEFAULT 0,
    dismissal_type  TEXT    NOT NULL,   -- caught | bowled | lbw | run_out | stumped | not_out | retired_hurt
    bowler_id       INTEGER             REFERENCES players(player_id)  -- NULL for run_out / not_out
);

CREATE TABLE IF NOT EXISTS bowling_figures (
    figure_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id        INTEGER NOT NULL REFERENCES matches(match_id),
    bowler_id       INTEGER NOT NULL REFERENCES players(player_id),
    bowling_team_id INTEGER NOT NULL REFERENCES teams(team_id),
    innings_number  INTEGER NOT NULL,   -- 1 or 2
    overs           REAL    NOT NULL,   -- e.g. 4.0, 3.2
    runs_conceded   INTEGER NOT NULL,
    wickets         INTEGER NOT NULL DEFAULT 0,
    dot_balls       INTEGER NOT NULL DEFAULT 0,
    wides           INTEGER NOT NULL DEFAULT 0,
    no_balls        INTEGER NOT NULL DEFAULT 0
);

-- Indexes on common join keys
CREATE INDEX IF NOT EXISTS idx_matches_season    ON matches(season_id);
CREATE INDEX IF NOT EXISTS idx_squads_match      ON match_squads(match_id);
CREATE INDEX IF NOT EXISTS idx_squads_player     ON match_squads(player_id);
CREATE INDEX IF NOT EXISTS idx_scorecard_match   ON innings_scorecards(match_id);
CREATE INDEX IF NOT EXISTS idx_scorecard_batter  ON innings_scorecards(batter_id);
CREATE INDEX IF NOT EXISTS idx_bowling_match     ON bowling_figures(match_id);
CREATE INDEX IF NOT EXISTS idx_bowling_bowler    ON bowling_figures(bowler_id);
"""

# ---------------------------------------------------------------------------
# Curated reference data — real-feeling IPL franchises
# ---------------------------------------------------------------------------
# (name, short_name, city, home_venue, founded_year, titles)
TEAMS_DATA: list[tuple[str, str, str, str, int, int]] = [
    ("Mumbai Indians",               "MI",  "Mumbai",    "Wankhede Stadium",                    2008, 5),
    ("Chennai Super Kings",          "CSK", "Chennai",   "MA Chidambaram Stadium",               2008, 5),
    ("Royal Challengers Bengaluru",  "RCB", "Bengaluru", "M Chinnaswamy Stadium",               2008, 1),
    ("Kolkata Knight Riders",        "KKR", "Kolkata",   "Eden Gardens",                        2008, 3),
    ("Delhi Capitals",               "DC",  "Delhi",     "Arun Jaitley Stadium",                2008, 0),
    ("Punjab Kings",                 "PBKS","Mohali",    "Punjab Cricket Association Stadium",  2008, 0),
    ("Rajasthan Royals",             "RR",  "Jaipur",    "Sawai Mansingh Stadium",              2008, 2),
    ("Sunrisers Hyderabad",          "SRH", "Hyderabad", "Rajiv Gandhi International Stadium",  2013, 1),
    ("Gujarat Titans",               "GT",  "Ahmedabad", "Narendra Modi Stadium",               2022, 2),
    ("Lucknow Super Giants",         "LSG", "Lucknow",   "BRSABV Ekana Cricket Stadium",        2022, 0),
]

# (name, city, capacity)
VENUES_DATA: list[tuple[str, str, int]] = [
    ("Wankhede Stadium",                    "Mumbai",    33000),
    ("MA Chidambaram Stadium",              "Chennai",   50000),
    ("M Chinnaswamy Stadium",               "Bengaluru", 35000),
    ("Eden Gardens",                        "Kolkata",   66000),
    ("Arun Jaitley Stadium",                "Delhi",     41000),
    ("Punjab Cricket Association Stadium",  "Mohali",    27000),
    ("Sawai Mansingh Stadium",              "Jaipur",    30000),
    ("Rajiv Gandhi International Stadium",  "Hyderabad", 55000),
    ("Narendra Modi Stadium",               "Ahmedabad", 132000),
    ("BRSABV Ekana Cricket Stadium",        "Lucknow",   50000),
    ("DY Patil Stadium",                    "Navi Mumbai",55000),
    ("Brabourne Stadium",                   "Mumbai",    20000),
]

# ---------------------------------------------------------------------------
# Curated player pools — realistic names by country
# ---------------------------------------------------------------------------
# (name, country, role, batting_style, bowling_style, is_overseas)
# role: batter | bowler | all-rounder | wicketkeeper
# bowling_style: right-arm fast | left-arm fast | right-arm medium | left-arm medium
#                right-arm off-spin | left-arm spin | right-arm leg-spin | none

SEED_PLAYERS: list[tuple[str, str, str, str, str, int]] = [
    # Indian batters
    ("Rohit Sharma",      "India",       "batter",       "right-hand", "right-arm medium",   0),
    ("Virat Kohli",       "India",       "batter",       "right-hand", "right-arm medium",   0),
    ("Shubman Gill",      "India",       "batter",       "right-hand", "none",               0),
    ("Ruturaj Gaikwad",   "India",       "batter",       "right-hand", "none",               0),
    ("KL Rahul",          "India",       "wicketkeeper", "right-hand", "none",               0),
    ("Ishan Kishan",      "India",       "wicketkeeper", "left-hand",  "none",               0),
    ("Shreyas Iyer",      "India",       "batter",       "right-hand", "none",               0),
    ("Sanju Samson",      "India",       "wicketkeeper", "right-hand", "none",               0),
    ("Prithvi Shaw",      "India",       "batter",       "right-hand", "none",               0),
    ("Devdutt Padikkal",  "India",       "batter",       "left-hand",  "none",               0),
    ("Suryakumar Yadav",  "India",       "batter",       "right-hand", "none",               0),
    ("Dinesh Karthik",    "India",       "wicketkeeper", "right-hand", "none",               0),
    ("Rishabh Pant",      "India",       "wicketkeeper", "left-hand",  "none",               0),
    ("Rajat Patidar",     "India",       "batter",       "right-hand", "none",               0),
    ("Tilak Varma",       "India",       "batter",       "left-hand",  "none",               0),
    ("Yashasvi Jaiswal",  "India",       "batter",       "left-hand",  "none",               0),
    # Indian all-rounders
    ("Hardik Pandya",     "India",       "all-rounder",  "right-hand", "right-arm fast",     0),
    ("Ravindra Jadeja",   "India",       "all-rounder",  "left-hand",  "left-arm spin",      0),
    ("Axar Patel",        "India",       "all-rounder",  "left-hand",  "left-arm spin",      0),
    ("Washington Sundar", "India",       "all-rounder",  "right-hand", "right-arm off-spin", 0),
    ("Krunal Pandya",     "India",       "all-rounder",  "left-hand",  "left-arm spin",      0),
    ("Venkatesh Iyer",    "India",       "all-rounder",  "left-hand",  "right-arm medium",   0),
    ("Nitish Rana",       "India",       "all-rounder",  "left-hand",  "right-arm off-spin", 0),
    ("Deepak Hooda",      "India",       "all-rounder",  "right-hand", "right-arm off-spin", 0),
    # Indian bowlers
    ("Jasprit Bumrah",    "India",       "bowler",       "right-hand", "right-arm fast",     0),
    ("Mohammed Shami",    "India",       "bowler",       "right-hand", "right-arm fast",     0),
    ("Bhuvneshwar Kumar", "India",       "bowler",       "right-hand", "right-arm medium",   0),
    ("Yuzvendra Chahal",  "India",       "bowler",       "right-hand", "right-arm leg-spin", 0),
    ("Ravichandran Ashwin","India",      "bowler",       "right-hand", "right-arm off-spin", 0),
    ("Kuldeep Yadav",     "India",       "bowler",       "left-hand",  "left-arm spin",      0),
    ("Mohit Sharma",      "India",       "bowler",       "right-hand", "right-arm medium",   0),
    ("Arshdeep Singh",    "India",       "bowler",       "left-hand",  "left-arm fast",      0),
    ("Umesh Yadav",       "India",       "bowler",       "right-hand", "right-arm fast",     0),
    ("Mohammed Siraj",    "India",       "bowler",       "right-hand", "right-arm fast",     0),
    ("Harshal Patel",     "India",       "bowler",       "right-hand", "right-arm medium",   0),
    ("T Natarajan",       "India",       "bowler",       "left-hand",  "left-arm fast",      0),
    ("Shardul Thakur",    "India",       "all-rounder",  "right-hand", "right-arm fast",     0),
    ("Deepak Chahar",     "India",       "bowler",       "right-hand", "right-arm medium",   0),
    ("Prasidh Krishna",   "India",       "bowler",       "right-hand", "right-arm fast",     0),
    # Australian players
    ("David Warner",      "Australia",   "batter",       "left-hand",  "right-arm off-spin", 1),
    ("Steve Smith",       "Australia",   "batter",       "right-hand", "right-arm leg-spin", 1),
    ("Glenn Maxwell",     "Australia",   "all-rounder",  "right-hand", "right-arm off-spin", 1),
    ("Pat Cummins",       "Australia",   "all-rounder",  "right-hand", "right-arm fast",     1),
    ("Mitchell Starc",    "Australia",   "bowler",       "left-hand",  "left-arm fast",      1),
    ("Josh Hazlewood",    "Australia",   "bowler",       "right-hand", "right-arm fast",     1),
    ("Marcus Stoinis",    "Australia",   "all-rounder",  "right-hand", "right-arm medium",   1),
    ("Aaron Finch",       "Australia",   "batter",       "right-hand", "none",               1),
    ("Matthew Wade",      "Australia",   "wicketkeeper", "left-hand",  "none",               1),
    # South African players
    ("Faf du Plessis",    "South Africa","batter",       "right-hand", "none",               1),
    ("Quinton de Kock",   "South Africa","wicketkeeper", "left-hand",  "none",               1),
    ("AB de Villiers",    "South Africa","batter",       "right-hand", "right-arm medium",   1),
    ("Kagiso Rabada",     "South Africa","bowler",       "right-hand", "right-arm fast",     1),
    ("Anrich Nortje",     "South Africa","bowler",       "right-hand", "right-arm fast",     1),
    ("Lungi Ngidi",       "South Africa","bowler",       "right-hand", "right-arm fast",     1),
    ("Marco Jansen",      "South Africa","all-rounder",  "left-hand",  "left-arm fast",      1),
    # English players
    ("Jos Buttler",       "England",     "wicketkeeper", "right-hand", "none",               1),
    ("Ben Stokes",        "England",     "all-rounder",  "left-hand",  "right-arm fast",     1),
    ("Sam Curran",        "England",     "all-rounder",  "left-hand",  "left-arm fast",      1),
    ("Liam Livingstone",  "England",     "all-rounder",  "right-hand", "right-arm leg-spin", 1),
    ("Jofra Archer",      "England",     "bowler",       "right-hand", "right-arm fast",     1),
    ("Mark Wood",         "England",     "bowler",       "right-hand", "right-arm fast",     1),
    ("Moeen Ali",         "England",     "all-rounder",  "left-hand",  "right-arm off-spin", 1),
    # New Zealand players
    ("Kane Williamson",   "New Zealand", "batter",       "right-hand", "right-arm off-spin", 1),
    ("Trent Boult",       "New Zealand", "bowler",       "right-hand", "left-arm fast",      1),
    ("Tim Southee",       "New Zealand", "bowler",       "right-hand", "right-arm medium",   1),
    ("Devon Conway",      "New Zealand", "wicketkeeper", "left-hand",  "none",               1),
    ("Lockie Ferguson",   "New Zealand", "bowler",       "right-hand", "right-arm fast",     1),
    # West Indian players
    ("Chris Gayle",       "West Indies", "batter",       "left-hand",  "right-arm off-spin", 1),
    ("Shimron Hetmyer",   "West Indies", "batter",       "left-hand",  "none",               1),
    ("Nicholas Pooran",   "West Indies", "wicketkeeper", "left-hand",  "none",               1),
    ("Sunil Narine",      "West Indies", "all-rounder",  "left-hand",  "right-arm off-spin", 1),
    ("Andre Russell",     "West Indies", "all-rounder",  "right-hand", "right-arm fast",     1),
    ("Jason Holder",      "West Indies", "all-rounder",  "right-hand", "right-arm medium",   1),
    ("Fabian Allen",      "West Indies", "all-rounder",  "left-hand",  "left-arm spin",      1),
    # Afghan players
    ("Rashid Khan",       "Afghanistan", "all-rounder",  "right-hand", "right-arm leg-spin", 1),
    ("Mohammad Nabi",     "Afghanistan", "all-rounder",  "right-hand", "right-arm off-spin", 1),
    ("Mujeeb Ur Rahman",  "Afghanistan", "bowler",       "right-hand", "right-arm off-spin", 1),
    ("Rahmanullah Gurbaz","Afghanistan", "wicketkeeper", "right-hand", "none",               1),
    # Sri Lankan players
    ("Kusal Perera",      "Sri Lanka",   "wicketkeeper", "left-hand",  "none",               1),
    ("Wanindu Hasaranga", "Sri Lanka",   "all-rounder",  "right-hand", "right-arm leg-spin", 1),
    ("Dushmantha Chameera","Sri Lanka",  "bowler",       "right-hand", "right-arm fast",     1),
    # Pakistani players (played in early IPL seasons)
    ("Shoaib Akhtar",     "Pakistan",    "bowler",       "right-hand", "right-arm fast",     1),
    ("Umar Gul",          "Pakistan",    "bowler",       "right-hand", "right-arm fast",     1),
]

# Roles and their bowling tendencies
ROLE_BOWLING_CHANCE: dict[str, float] = {
    "batter":       0.05,   # batters rarely bowl
    "bowler":       0.95,   # bowlers almost always bowl
    "all-rounder":  0.80,   # all-rounders bowl often
    "wicketkeeper": 0.02,   # keepers never bowl
}

DISMISSAL_TYPES = [
    "caught", "bowled", "lbw", "run_out", "stumped", "not_out", "retired_hurt"
]
DISMISSAL_WEIGHTS = [0.42, 0.18, 0.10, 0.12, 0.05, 0.12, 0.01]

TOSS_DECISIONS = ["bat", "field"]
TOSS_DECISION_WEIGHTS = [0.40, 0.60]   # teams tend to field after winning toss in T20

MATCH_TYPES_LEAGUE = ["league"]
MATCH_TYPES_PLAYOFF = ["qualifier1", "eliminator", "qualifier2", "final"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def rand_date(start: date, end: date) -> date:
    delta = (end - start).days
    if delta <= 0:
        return start
    return start + timedelta(days=random.randint(0, delta))


def ipl_season_dates(year: int) -> tuple[date, date]:
    """Return approximate IPL season start and end dates."""
    return date(year, 3, 22), date(year, 5, 29)


def realistic_batting_row(
    batting_order: int,
    role: str,
) -> tuple[int, int, int, int]:
    """Return (runs, balls_faced, fours, sixes) with realistic IPL ranges.

    Top-order batters (positions 1-4) face more balls and score more.
    Lower-order batters (5-11) have shorter, more explosive innings.
    Strike rates biased toward 120-160 for openers, 140-200 for finishers.
    """
    if batting_order <= 2:  # openers
        balls = random.randint(10, 65)
        strike_rate = random.uniform(1.10, 1.75)
    elif batting_order <= 4:  # top-order
        balls = random.randint(8, 50)
        strike_rate = random.uniform(1.15, 1.85)
    elif batting_order <= 7:  # middle-order
        balls = random.randint(5, 35)
        strike_rate = random.uniform(1.20, 1.95)
    else:  # lower-order
        balls = random.randint(1, 20)
        strike_rate = random.uniform(1.00, 2.20)

    # Bowlers get fewer balls
    if role == "bowler":
        balls = random.randint(1, 12)
        strike_rate = random.uniform(0.90, 1.60)

    runs = int(balls * strike_rate)
    # Distribute boundaries: ~60% of runs from boundaries (realistic T20 ratio)
    boundary_runs = int(runs * random.uniform(0.45, 0.70))
    sixes_portion = int(boundary_runs * random.uniform(0.25, 0.55))
    fours_portion = boundary_runs - sixes_portion
    sixes = sixes_portion // 6
    fours = fours_portion // 4
    return runs, balls, fours, sixes


def realistic_bowling_spell(
    bowler_role: str,
    economy_bias: str = "normal",  # "tight" | "normal" | "expensive"
) -> tuple[float, int, int, int, int, int]:
    """Return (overs, runs_conceded, wickets, dot_balls, wides, no_balls).

    IPL bowlers bowl 1-4 overs each (max 4 in T20).
    Economy rates realistic: 6-10 runs/over for most bowlers.
    """
    overs_whole = random.randint(1, 4)
    # Legal balls in complete overs; occasionally cut short
    fraction = random.choice([0, 0, 0, 0, 1, 2, 3, 4, 5])  # partial overs rare
    if fraction > 0 and overs_whole < 4:
        overs = overs_whole + fraction / 10
    else:
        overs = float(overs_whole)
        fraction = 0

    total_balls = overs_whole * 6 + fraction

    if economy_bias == "tight":
        economy = random.uniform(5.5, 7.5)
    elif economy_bias == "expensive":
        economy = random.uniform(9.0, 12.0)
    else:
        economy = random.uniform(7.0, 10.0)

    runs_conceded = max(0, int(overs * economy + random.gauss(0, 2)))

    # Wickets: most spells 0-2, premium bowlers occasionally 3+
    if bowler_role in ("bowler", "all-rounder"):
        wicket_probs = [0.42, 0.30, 0.18, 0.07, 0.03]
    else:
        wicket_probs = [0.70, 0.22, 0.06, 0.01, 0.01]
    wickets = random.choices([0, 1, 2, 3, 4], weights=wicket_probs, k=1)[0]
    wickets = min(wickets, total_balls // 6 + 1)   # sanity cap

    dot_balls = int(total_balls * random.uniform(0.25, 0.55))
    wides = random.randint(0, 4)
    no_balls = random.randint(0, 2)

    return overs, runs_conceded, wickets, dot_balls, wides, no_balls


# ---------------------------------------------------------------------------
# Assign a squad of 11 to each team for a match
# ---------------------------------------------------------------------------
def assign_squad(
    team_id: int,
    team_pool: list[int],  # player_ids for this team
    player_role_map: dict[int, str],
) -> list[tuple[int, int, int]]:
    """Return list of (player_id, is_captain, is_keeper) for 11 players."""
    # Ensure we have at least one keeper and 3-4 bowlers
    keepers = [p for p in team_pool if player_role_map[p] == "wicketkeeper"]
    bowlers = [p for p in team_pool if player_role_map[p] in ("bowler", "all-rounder")]
    others = [p for p in team_pool if p not in keepers and p not in bowlers]

    selected: list[int] = []

    # Pick 1 keeper
    keeper = random.choice(keepers) if keepers else random.choice(team_pool)
    selected.append(keeper)

    # Pick 3-4 pure bowlers / all-rounders
    n_bowl = random.randint(3, 4)
    bowl_sample = random.sample(bowlers, min(n_bowl, len(bowlers)))
    selected.extend(bowl_sample)

    # Fill rest from others, avoiding duplicates
    remaining_pool = [p for p in team_pool if p not in selected]
    need = 11 - len(selected)
    fill = random.sample(remaining_pool, min(need, len(remaining_pool)))
    selected.extend(fill)

    # If still under 11 (small team pool), sample from full team pool
    if len(selected) < 11:
        extra_pool = [p for p in team_pool if p not in selected]
        selected.extend(random.sample(extra_pool, min(11 - len(selected), len(extra_pool))))

    selected = selected[:11]
    if len(selected) < 11:
        return []  # skip if can't fill 11

    # Assign captain: prefer all-rounder > batter
    candidates_for_captain = [p for p in selected if player_role_map[p] in ("batter", "all-rounder")]
    captain = random.choice(candidates_for_captain) if candidates_for_captain else random.choice(selected)

    result = []
    for p in selected:
        is_cap = 1 if p == captain else 0
        is_kp = 1 if p == keeper else 0
        result.append((p, is_cap, is_kp))
    return result


# ---------------------------------------------------------------------------
# Build everything in memory, then insert in FK-respecting order
# ---------------------------------------------------------------------------
def build_db(conn: sqlite3.Connection) -> None:  # noqa: C901
    conn.executescript(DDL)

    # ------------------------------------------------------------------
    # 1. Teams
    # ------------------------------------------------------------------
    team_ids: list[int] = []
    for name, short, city, home, founded, titles in TEAMS_DATA:
        cur = conn.execute(
            "INSERT INTO teams (name, short_name, city, home_venue, founded_year, titles)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (name, short, city, home, founded, titles),
        )
        team_ids.append(cur.lastrowid)  # type: ignore[arg-type]

    team_name_to_id: dict[str, int] = {TEAMS_DATA[i][0]: team_ids[i] for i in range(len(TEAMS_DATA))}
    team_home_venue: dict[int, str] = {team_ids[i]: TEAMS_DATA[i][3] for i in range(len(TEAMS_DATA))}

    # ------------------------------------------------------------------
    # 2. Venues
    # ------------------------------------------------------------------
    venue_ids: list[int] = []
    venue_name_to_id: dict[str, int] = {}
    for name, city, cap in VENUES_DATA:
        cur = conn.execute(
            "INSERT INTO venues (name, city, capacity) VALUES (?, ?, ?)",
            (name, city, cap),
        )
        vid = cur.lastrowid  # type: ignore[assignment]
        venue_ids.append(vid)
        venue_name_to_id[name] = vid

    # Map home venue name → venue_id
    team_home_venue_id: dict[int, int] = {}
    for tid, vname in team_home_venue.items():
        team_home_venue_id[tid] = venue_name_to_id.get(vname, venue_ids[0])

    # ------------------------------------------------------------------
    # 3. Players
    # ------------------------------------------------------------------
    player_ids: list[int] = []
    player_role_map: dict[int, str] = {}
    player_bowling_style_map: dict[int, str] = {}

    # Build from curated seed list
    seed_player_ids: list[int] = []
    for name, country, role, bat_style, bowl_style, is_overseas in SEED_PLAYERS:
        dob = rand_date(date(1988, 1, 1), date(2002, 12, 31))
        cur = conn.execute(
            "INSERT INTO players (name, country, role, batting_style, bowling_style,"
            " date_of_birth, is_overseas) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, country, role, bat_style, bowl_style, dob.isoformat(), is_overseas),
        )
        pid = cur.lastrowid  # type: ignore[assignment]
        seed_player_ids.append(pid)
        player_ids.append(pid)
        player_role_map[pid] = role
        player_bowling_style_map[pid] = bowl_style

    # Fill remaining players with Faker names to reach ~160 total
    ROLES = ["batter", "bowler", "all-rounder", "wicketkeeper"]
    ROLE_WEIGHTS = [0.35, 0.30, 0.25, 0.10]
    BAT_STYLES = ["right-hand", "left-hand"]
    BAT_WEIGHTS = [0.68, 0.32]
    BOWL_STYLES_BY_ROLE: dict[str, list[str]] = {
        "batter":       ["none"],
        "wicketkeeper": ["none"],
        "bowler":       ["right-arm fast", "left-arm fast", "right-arm medium",
                         "left-arm medium", "right-arm off-spin", "left-arm spin", "right-arm leg-spin"],
        "all-rounder":  ["right-arm fast", "left-arm fast", "right-arm medium",
                         "left-arm medium", "right-arm off-spin", "left-arm spin", "right-arm leg-spin"],
    }
    BOWL_WEIGHTS = [0.20, 0.12, 0.18, 0.08, 0.18, 0.14, 0.10]

    FILLER_COUNTRIES = [
        ("India", 0, 0.55),
        ("Australia", 1, 0.10),
        ("South Africa", 1, 0.08),
        ("England", 1, 0.07),
        ("New Zealand", 1, 0.06),
        ("West Indies", 1, 0.05),
        ("Afghanistan", 1, 0.04),
        ("Sri Lanka", 1, 0.03),
        ("Bangladesh", 1, 0.02),
    ]

    n_existing = len(SEED_PLAYERS)
    n_filler = 160 - n_existing

    for _ in range(n_filler):
        # Pick country
        country_weights = [c[2] for c in FILLER_COUNTRIES]
        chosen = random.choices(FILLER_COUNTRIES, weights=country_weights, k=1)[0]
        country, is_overseas, _ = chosen

        role = random.choices(ROLES, weights=ROLE_WEIGHTS, k=1)[0]
        bat_style = random.choices(BAT_STYLES, weights=BAT_WEIGHTS, k=1)[0]
        bowl_styles_list = BOWL_STYLES_BY_ROLE[role]
        if role in ("bowler", "all-rounder"):
            bowl_style = random.choices(bowl_styles_list, weights=BOWL_WEIGHTS, k=1)[0]
        else:
            bowl_style = "none"

        name = fake.name()
        dob = rand_date(date(1990, 1, 1), date(2004, 12, 31))

        cur = conn.execute(
            "INSERT INTO players (name, country, role, batting_style, bowling_style,"
            " date_of_birth, is_overseas) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, country, role, bat_style, bowl_style, dob.isoformat(), is_overseas),
        )
        pid = cur.lastrowid  # type: ignore[assignment]
        player_ids.append(pid)
        player_role_map[pid] = role
        player_bowling_style_map[pid] = bowl_style

    # Separate by overseas/domestic
    indian_player_ids = [pid for pid in player_ids
                         if player_role_map.get(pid) is not None
                         and (pid < seed_player_ids[0] + n_existing + 1)]
    # Re-derive properly by querying our maps: seed players have known is_overseas
    # Build overseas flag map
    overseas_flag: dict[int, int] = {}
    for i, (_, _, _, _, _, is_ov) in enumerate(SEED_PLAYERS):
        overseas_flag[seed_player_ids[i]] = is_ov
    # Filler players: determine from index — first 55% of filler are Indian (is_overseas=0)
    # We can't easily backtrack; just query the DB
    rows = conn.execute("SELECT player_id, is_overseas FROM players").fetchall()
    overseas_flag = {r[0]: r[1] for r in rows}

    domestic_ids = [pid for pid, ov in overseas_flag.items() if ov == 0]
    overseas_ids = [pid for pid, ov in overseas_flag.items() if ov == 1]

    # ------------------------------------------------------------------
    # 4. Assign players to teams
    # Each team gets 18-22 contracted players; max 4 overseas per playing XI
    # We'll create a team roster (not a DB table, just for seeding logic)
    # ------------------------------------------------------------------
    N_TEAMS = len(team_ids)
    team_roster: dict[int, list[int]] = {tid: [] for tid in team_ids}

    # Distribute overseas players ~4-5 per team
    random.shuffle(overseas_ids)
    for i, oid in enumerate(overseas_ids):
        team_roster[team_ids[i % N_TEAMS]].append(oid)

    # Distribute domestic players evenly
    random.shuffle(domestic_ids)
    per_team_domestic = len(domestic_ids) // N_TEAMS
    for i, tid in enumerate(team_ids):
        start = i * per_team_domestic
        end = start + per_team_domestic if i < N_TEAMS - 1 else len(domestic_ids)
        team_roster[tid].extend(domestic_ids[start:end])

    # Ensure each team has at least 1 keeper and 3 bowlers
    # (if not, swap in from filler)
    for tid in team_ids:
        pool = team_roster[tid]
        keepers_in_pool = [p for p in pool if player_role_map[p] == "wicketkeeper"]
        bowlers_in_pool = [p for p in pool if player_role_map[p] in ("bowler", "all-rounder")]
        if not keepers_in_pool:
            # grab any keeper from domestic_ids not already assigned
            unassigned_keepers = [p for p in domestic_ids
                                   if player_role_map[p] == "wicketkeeper"
                                   and all(p not in roster for roster in team_roster.values())]
            if unassigned_keepers:
                team_roster[tid].append(unassigned_keepers[0])

    # ------------------------------------------------------------------
    # 5. Seasons
    # ------------------------------------------------------------------
    # Historical winners (real-ish, 2020-2024)
    SEASON_WINNERS: dict[int, tuple[str, str]] = {
        2020: ("Mumbai Indians",              "Delhi Capitals"),
        2021: ("Chennai Super Kings",         "Kolkata Knight Riders"),
        2022: ("Gujarat Titans",              "Rajasthan Royals"),
        2023: ("Chennai Super Kings",         "Gujarat Titans"),
        2024: ("Kolkata Knight Riders",       "Sunrisers Hyderabad"),
    }

    season_ids: dict[int, int] = {}
    for year in range(2020, 2025):
        w_name, r_name = SEASON_WINNERS[year]
        w_id = team_name_to_id.get(w_name)
        r_id = team_name_to_id.get(r_name)
        final_venue = random.choice(venue_ids)
        cur = conn.execute(
            "INSERT INTO seasons (year, winning_team_id, runner_up_id, final_venue_id)"
            " VALUES (?, ?, ?, ?)",
            (year, w_id, r_id, final_venue),
        )
        season_ids[year] = cur.lastrowid  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # 6. Matches — ~70 per season, with playoffs at end
    # ------------------------------------------------------------------
    # Round-robin: 10 teams, each plays 14 league games (home+away vs 7 others)
    # Then 4 playoff matches. Total: 70 per season.
    match_ids_all: list[int] = []
    all_match_records: list[dict] = []  # for squad/scorecard generation

    for year in range(2020, 2025):
        sid = season_ids[year]
        season_start, season_end = ipl_season_dates(year)

        # Generate ~66 league matches: round-robin style
        matchups: list[tuple[int, int]] = []
        for i in range(N_TEAMS):
            for j in range(i + 1, N_TEAMS):
                matchups.append((team_ids[i], team_ids[j]))
        # Each pair plays twice (home & away alternating by year)
        league_fixtures: list[tuple[int, int]] = []
        for ta, tb in matchups:
            league_fixtures.append((ta, tb))
            league_fixtures.append((tb, ta))  # reverse = "away"
        random.shuffle(league_fixtures)
        league_fixtures = league_fixtures[:66]  # cap at 66

        # Distribute match dates across the season
        total_league_days = (season_end - season_start).days - 10  # leave room for playoffs
        match_dates_league = sorted([
            season_start + timedelta(days=int(total_league_days * i / len(league_fixtures)))
            for i in range(len(league_fixtures))
        ])

        # Insert league matches
        for idx, (ta, tb) in enumerate(league_fixtures):
            match_date = match_dates_league[idx]
            # Venue: usually home team's ground, occasionally neutral
            if random.random() < 0.72:
                venue_id = team_home_venue_id.get(ta, random.choice(venue_ids))
            else:
                venue_id = random.choice(venue_ids)

            toss_winner = random.choice([ta, tb])
            toss_decision = random.choices(TOSS_DECISIONS, weights=TOSS_DECISION_WEIGHTS, k=1)[0]

            # Decide winner (slight home advantage)
            no_result = random.random() < 0.02  # 2% chance of no result
            if no_result:
                winner_id = None
                win_margin_runs = None
                win_margin_wickets = None
            else:
                if ta == toss_winner and toss_decision == "bat":
                    # Batting first team (ta) wins 45% if they chose to bat
                    winner_id = ta if random.random() < 0.45 else tb
                else:
                    # Chasing team wins ~55% in T20
                    winner_id = tb if random.random() < 0.55 else ta

                # Win margin
                batting_first = ta if toss_decision == "bat" and toss_winner == ta else (
                    tb if toss_decision == "bat" and toss_winner == tb else ta
                )
                if winner_id == batting_first:
                    # Won by runs
                    win_margin_runs = random.randint(3, 85)
                    win_margin_wickets = None
                else:
                    win_margin_runs = None
                    win_margin_wickets = random.randint(1, 10)

            cur = conn.execute(
                """INSERT INTO matches
                   (season_id, match_date, team_a_id, team_b_id, venue_id,
                    toss_winner_id, toss_decision, winner_id,
                    win_margin_runs, win_margin_wickets, is_playoff, match_type)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'league')""",
                (sid, match_date.isoformat(), ta, tb, venue_id,
                 toss_winner, toss_decision, winner_id,
                 win_margin_runs, win_margin_wickets),
            )
            mid = cur.lastrowid  # type: ignore[assignment]
            match_ids_all.append(mid)
            all_match_records.append({
                "match_id": mid, "season_id": sid, "year": year,
                "team_a": ta, "team_b": tb,
                "toss_winner": toss_winner, "toss_decision": toss_decision,
                "winner_id": winner_id,
                "win_margin_runs": win_margin_runs,
                "win_margin_wickets": win_margin_wickets,
            })

        # 4 playoff matches at end of season
        # Playoff teams: top 4 by pseudo-random selection (weighted by titles)
        title_weights = [TEAMS_DATA[team_ids.index(tid)][5] + 1 for tid in team_ids]
        top4 = random.choices(team_ids, weights=title_weights, k=4)
        # Deduplicate while preserving order
        seen: set[int] = set()
        top4_unique: list[int] = []
        for t in top4:
            if t not in seen:
                top4_unique.append(t)
                seen.add(t)
        while len(top4_unique) < 4:
            extra = random.choice([t for t in team_ids if t not in seen])
            top4_unique.append(extra)
            seen.add(extra)

        playoff_fixtures = [
            (top4_unique[0], top4_unique[1], "qualifier1"),
            (top4_unique[2], top4_unique[3], "eliminator"),
            (top4_unique[0], top4_unique[2], "qualifier2"),  # simplified
            (team_name_to_id[SEASON_WINNERS[year][0]], team_name_to_id[SEASON_WINNERS[year][1]], "final"),
        ]

        playoff_start = season_end - timedelta(days=8)
        for po_idx, (ta, tb, ptype) in enumerate(playoff_fixtures):
            match_date = playoff_start + timedelta(days=po_idx * 2)
            venue_id = venue_name_to_id.get("Narendra Modi Stadium", random.choice(venue_ids))
            toss_winner = random.choice([ta, tb])
            toss_decision = random.choices(TOSS_DECISIONS, weights=TOSS_DECISION_WEIGHTS, k=1)[0]

            # Final winner matches historical record
            if ptype == "final":
                winner_id = team_name_to_id[SEASON_WINNERS[year][0]]
            else:
                winner_id = random.choice([ta, tb])

            batting_first = ta if toss_decision == "bat" and toss_winner == ta else (
                tb if toss_decision == "bat" and toss_winner == tb else ta
            )
            if winner_id == batting_first:
                win_margin_runs = random.randint(5, 65)
                win_margin_wickets = None
            else:
                win_margin_runs = None
                win_margin_wickets = random.randint(2, 8)

            cur = conn.execute(
                """INSERT INTO matches
                   (season_id, match_date, team_a_id, team_b_id, venue_id,
                    toss_winner_id, toss_decision, winner_id,
                    win_margin_runs, win_margin_wickets, is_playoff, match_type)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
                (sid, match_date.isoformat(), ta, tb, venue_id,
                 toss_winner, toss_decision, winner_id,
                 win_margin_runs, win_margin_wickets, ptype),
            )
            mid = cur.lastrowid  # type: ignore[assignment]
            match_ids_all.append(mid)
            all_match_records.append({
                "match_id": mid, "season_id": sid, "year": year,
                "team_a": ta, "team_b": tb,
                "toss_winner": toss_winner, "toss_decision": toss_decision,
                "winner_id": winner_id,
                "win_margin_runs": win_margin_runs,
                "win_margin_wickets": win_margin_wickets,
            })

    # Update season total_matches
    for year, sid in season_ids.items():
        (cnt,) = conn.execute(
            "SELECT COUNT(*) FROM matches WHERE season_id = ?", (sid,)
        ).fetchone()
        conn.execute("UPDATE seasons SET total_matches = ? WHERE season_id = ?", (cnt, sid))

    # ------------------------------------------------------------------
    # 7. Match squads + innings scorecards + bowling figures
    #    Process each match, insert squads, then batting rows, then bowling rows
    # ------------------------------------------------------------------
    for rec in all_match_records:
        mid = rec["match_id"]
        ta = rec["team_a"]
        tb = rec["team_b"]

        pool_a = team_roster.get(ta, [])
        pool_b = team_roster.get(tb, [])

        # Skip if roster too small
        if len(pool_a) < 11 or len(pool_b) < 11:
            continue

        squad_a = assign_squad(ta, pool_a, player_role_map)
        squad_b = assign_squad(tb, pool_b, player_role_map)

        if len(squad_a) < 11 or len(squad_b) < 11:
            continue

        # Guard: remove any player from squad_b that also appears in squad_a
        # (should be rare but protects against roster overlap edge cases)
        squad_a_pid_set: set[int] = {p for (p, _, _) in squad_a}
        squad_b = [(p, c, k) for (p, c, k) in squad_b if p not in squad_a_pid_set]
        # Refill squad_b from pool_b if we lost any players
        if len(squad_b) < 11:
            pool_b_clean = [p for p in pool_b if p not in squad_a_pid_set]
            already_in_b = {p for (p, _, _) in squad_b}
            extras = [p for p in pool_b_clean if p not in already_in_b]
            for ep in extras:
                if len(squad_b) >= 11:
                    break
                squad_b.append((ep, 0, 0))
        if len(squad_b) < 11:
            continue

        # Insert squad rows
        squad_a_pids: list[int] = []
        squad_b_pids: list[int] = []
        for (pid, is_cap, is_kp) in squad_a:
            conn.execute(
                "INSERT OR IGNORE INTO match_squads"
                " (match_id, player_id, team_id, is_captain, is_keeper)"
                " VALUES (?, ?, ?, ?, ?)",
                (mid, pid, ta, is_cap, is_kp),
            )
            squad_a_pids.append(pid)
        for (pid, is_cap, is_kp) in squad_b:
            conn.execute(
                "INSERT OR IGNORE INTO match_squads"
                " (match_id, player_id, team_id, is_captain, is_keeper)"
                " VALUES (?, ?, ?, ?, ?)",
                (mid, pid, tb, is_cap, is_kp),
            )
            squad_b_pids.append(pid)

        # Determine batting order for each innings
        # Innings 1: team_a bats (if team_a won toss and chose bat, or team_b chose field)
        toss_winner = rec["toss_winner"]
        toss_decision = rec["toss_decision"]
        if (toss_winner == ta and toss_decision == "bat") or \
           (toss_winner == tb and toss_decision == "field"):
            inning1_batting = ta
            inning1_batting_squad = squad_a_pids
            inning1_bowling_squad = squad_b_pids
            inning2_batting = tb
            inning2_batting_squad = squad_b_pids
            inning2_bowling_squad = squad_a_pids
        else:
            inning1_batting = tb
            inning1_batting_squad = squad_b_pids
            inning1_bowling_squad = squad_a_pids
            inning2_batting = ta
            inning2_batting_squad = squad_a_pids
            inning2_bowling_squad = squad_b_pids

        # Generate 2 innings
        for innings_num, (batting_team, batting_squad, bowling_squad) in enumerate([
            (inning1_batting, inning1_batting_squad, inning1_bowling_squad),
            (inning2_batting, inning2_batting_squad, inning2_bowling_squad),
        ], start=1):

            # Batting: 6-9 batters face deliveries (not always all 11 out in T20)
            n_batters = random.randint(6, 9)
            batting_order_ids = batting_squad[:n_batters]

            # Build valid bowler list: eligible to bowl (role not keeper, bowling_style != none)
            eligible_bowlers = [
                pid for pid in bowling_squad
                if player_role_map.get(pid) != "wicketkeeper"
                and player_bowling_style_map.get(pid, "none") != "none"
            ]
            if not eligible_bowlers:
                eligible_bowlers = [pid for pid in bowling_squad
                                    if player_role_map.get(pid) != "wicketkeeper"]
            if not eligible_bowlers:
                eligible_bowlers = bowling_squad

            for batting_pos, batter_id in enumerate(batting_order_ids, start=1):
                role = player_role_map.get(batter_id, "batter")
                runs, balls, fours, sixes = realistic_batting_row(batting_pos, role)

                # Dismissal
                dismissal = random.choices(DISMISSAL_TYPES, weights=DISMISSAL_WEIGHTS, k=1)[0]
                # Last batter or forced not-out
                if batting_pos == n_batters:
                    dismissal = "not_out"

                # Bowler credited (not for run_out or not_out)
                bowler_id: int | None = None
                if dismissal not in ("not_out", "run_out", "retired_hurt") and eligible_bowlers:
                    bowler_id = random.choice(eligible_bowlers)

                conn.execute(
                    """INSERT INTO innings_scorecards
                       (match_id, batting_team_id, innings_number, batter_id,
                        batting_order, runs, balls_faced, fours, sixes,
                        dismissal_type, bowler_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (mid, batting_team, innings_num, batter_id,
                     batting_pos, runs, balls, fours, sixes,
                     dismissal, bowler_id),
                )

            # Bowling figures: 4-6 unique bowlers per innings
            n_bowlers = random.randint(4, 6)
            bowlers_this_innings = random.sample(
                eligible_bowlers, min(n_bowlers, len(eligible_bowlers))
            )

            # Assign economy bias based on match context
            for bowler_id in bowlers_this_innings:
                b_role = player_role_map.get(bowler_id, "bowler")
                # Specialist bowlers tend to be tighter
                if b_role == "bowler":
                    bias = random.choices(["tight", "normal", "expensive"],
                                          weights=[0.35, 0.50, 0.15], k=1)[0]
                else:
                    bias = random.choices(["tight", "normal", "expensive"],
                                          weights=[0.20, 0.55, 0.25], k=1)[0]

                overs, runs_c, wickets, dots, wides, no_balls = realistic_bowling_spell(b_role, bias)

                # Determine bowling team
                bowling_team_id = (
                    ta if batting_team == tb else tb
                )
                conn.execute(
                    """INSERT INTO bowling_figures
                       (match_id, bowler_id, bowling_team_id, innings_number,
                        overs, runs_conceded, wickets, dot_balls, wides, no_balls)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (mid, bowler_id, bowling_team_id, innings_num,
                     overs, runs_c, wickets, dots, wides, no_balls),
                )

    conn.commit()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        build_db(conn)
    finally:
        conn.close()

    # Row-count summary
    conn_r = sqlite3.connect(str(DB_PATH))
    tables = [
        "teams", "venues", "players", "seasons",
        "matches", "match_squads", "innings_scorecards", "bowling_figures",
    ]
    total = 0
    for t in tables:
        (n,) = conn_r.execute(f"SELECT COUNT(*) FROM {t}").fetchone()
        total += n
    conn_r.close()

    print(f"ipl.db ready · {len(tables)} tables · {total} total rows")


if __name__ == "__main__":
    main()

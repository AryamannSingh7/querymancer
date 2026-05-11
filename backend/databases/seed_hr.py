"""Seed script for the HR sample database.

Creates backend/databases/hr.db from scratch (drops and recreates).
Uses Faker(seed=42) + random.seed(42) for full reproducibility.

Tables:
  departments        — lookup: org units
  job_titles         — lookup: role catalogue
  employees          — core people table, self-referential manager_id FK
  salary_history     — one row per raise event (1-3 per employee)
  performance_reviews— annual/semi-annual review records
  time_off_requests  — PTO / sick / parental leave rows
  dependents         — family members tied to an employee

Run:
    cd backend
    .venv/Scripts/python.exe databases/seed_hr.py
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
DB_PATH = Path(__file__).resolve().parent / "hr.db"


# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------
DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS departments (
    department_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    location        TEXT    NOT NULL,
    budget          REAL    NOT NULL   -- annual budget USD
);

CREATE TABLE IF NOT EXISTS job_titles (
    job_title_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT    NOT NULL UNIQUE,
    job_family      TEXT    NOT NULL,  -- e.g. Engineering, Sales, Finance
    min_salary      REAL    NOT NULL,
    max_salary      REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS employees (
    employee_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name      TEXT    NOT NULL,
    last_name       TEXT    NOT NULL,
    email           TEXT    NOT NULL UNIQUE,
    phone           TEXT,
    hire_date       DATE    NOT NULL,
    birth_date      DATE    NOT NULL,
    gender          TEXT    NOT NULL,   -- M / F / NB
    department_id   INTEGER NOT NULL REFERENCES departments(department_id),
    job_title_id    INTEGER NOT NULL REFERENCES job_titles(job_title_id),
    manager_id      INTEGER             REFERENCES employees(employee_id),
    status          TEXT    NOT NULL DEFAULT 'active',  -- active / inactive
    city            TEXT    NOT NULL,
    country         TEXT    NOT NULL DEFAULT 'US'
);

CREATE TABLE IF NOT EXISTS salary_history (
    salary_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id     INTEGER NOT NULL REFERENCES employees(employee_id),
    effective_from  DATE    NOT NULL,
    salary          REAL    NOT NULL,
    change_reason   TEXT    NOT NULL   -- hire / merit / promotion / market_adj
);

CREATE TABLE IF NOT EXISTS performance_reviews (
    review_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id     INTEGER NOT NULL REFERENCES employees(employee_id),
    reviewer_id     INTEGER NOT NULL REFERENCES employees(employee_id),
    review_date     DATE    NOT NULL,
    period_start    DATE    NOT NULL,
    period_end      DATE    NOT NULL,
    rating          INTEGER NOT NULL,  -- 1 (poor) … 5 (exceptional)
    comments        TEXT
);

CREATE TABLE IF NOT EXISTS time_off_requests (
    request_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id     INTEGER NOT NULL REFERENCES employees(employee_id),
    leave_type      TEXT    NOT NULL,  -- pto / sick / parental / unpaid
    start_date      DATE    NOT NULL,
    end_date        DATE    NOT NULL,
    days_requested  INTEGER NOT NULL,
    status          TEXT    NOT NULL,  -- pending / approved / denied
    approved_by     INTEGER             REFERENCES employees(employee_id),
    requested_on    DATE    NOT NULL
);

CREATE TABLE IF NOT EXISTS dependents (
    dependent_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id     INTEGER NOT NULL REFERENCES employees(employee_id),
    first_name      TEXT    NOT NULL,
    last_name       TEXT    NOT NULL,
    relationship    TEXT    NOT NULL,  -- spouse / child / parent / domestic_partner
    birth_date      DATE    NOT NULL
);
"""

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------
DEPARTMENTS: list[tuple[str, str, float]] = [
    ("Engineering",       "San Francisco, CA",  4_200_000),
    ("Sales",             "New York, NY",        3_100_000),
    ("Marketing",         "Chicago, IL",         1_800_000),
    ("Human Resources",   "Austin, TX",            950_000),
    ("Finance",           "New York, NY",        2_400_000),
    ("Customer Support",  "Phoenix, AZ",           780_000),
    ("Operations",        "Dallas, TX",          1_650_000),
    ("Legal",             "Washington, DC",        720_000),
]

# (title, job_family, min_salary, max_salary)
JOB_TITLES: list[tuple[str, str, float, float]] = [
    # Engineering
    ("Junior Software Engineer",    "Engineering",  65_000,  90_000),
    ("Software Engineer",           "Engineering",  90_000, 130_000),
    ("Senior Software Engineer",    "Engineering", 130_000, 170_000),
    ("Staff Engineer",              "Engineering", 165_000, 215_000),
    ("Engineering Manager",         "Engineering", 175_000, 230_000),
    ("VP of Engineering",           "Engineering", 230_000, 310_000),
    # Sales
    ("Sales Development Rep",       "Sales",        48_000,  72_000),
    ("Account Executive",           "Sales",        70_000, 110_000),
    ("Senior Account Executive",    "Sales",       100_000, 145_000),
    ("Sales Manager",               "Sales",       120_000, 160_000),
    ("VP of Sales",                 "Sales",       185_000, 260_000),
    # Marketing
    ("Marketing Coordinator",       "Marketing",    45_000,  65_000),
    ("Marketing Manager",           "Marketing",    80_000, 115_000),
    ("Growth Marketer",             "Marketing",    75_000, 110_000),
    ("Head of Marketing",           "Marketing",   140_000, 185_000),
    # HR
    ("HR Coordinator",              "HR",           45_000,  65_000),
    ("HR Business Partner",         "HR",           75_000, 105_000),
    ("HR Director",                 "HR",          115_000, 150_000),
    # Finance
    ("Financial Analyst",           "Finance",      60_000,  90_000),
    ("Senior Financial Analyst",    "Finance",      88_000, 120_000),
    ("Finance Manager",             "Finance",     115_000, 150_000),
    ("CFO",                         "Finance",     220_000, 310_000),
    # Customer Support
    ("Support Specialist",          "Support",      38_000,  55_000),
    ("Support Lead",                "Support",      55_000,  75_000),
    ("Support Manager",             "Support",      75_000, 100_000),
    # Operations
    ("Operations Analyst",          "Operations",   55_000,  80_000),
    ("Operations Manager",          "Operations",   90_000, 125_000),
    ("VP of Operations",            "Operations",  160_000, 220_000),
    # Legal
    ("Legal Counsel",               "Legal",       120_000, 170_000),
    ("General Counsel",             "Legal",       200_000, 280_000),
]

GENDERS = ["M", "F", "NB"]
GENDER_WEIGHTS = [0.48, 0.48, 0.04]

CHANGE_REASONS = ["merit", "promotion", "market_adj"]
LEAVE_TYPES = ["pto", "sick", "parental", "unpaid"]
LEAVE_TYPE_WEIGHTS = [0.60, 0.25, 0.10, 0.05]
LEAVE_STATUSES = ["pending", "approved", "denied"]
LEAVE_STATUS_WEIGHTS = [0.10, 0.82, 0.08]
RELATIONSHIPS = ["spouse", "child", "parent", "domestic_partner"]
RELATIONSHIP_WEIGHTS = [0.35, 0.40, 0.15, 0.10]
REVIEW_RATINGS = [1, 2, 3, 4, 5]
REVIEW_RATING_WEIGHTS = [0.04, 0.10, 0.35, 0.35, 0.16]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def rand_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def salary_in_band(min_s: float, max_s: float) -> float:
    """Return a salary rounded to the nearest $500 within the band."""
    raw = random.uniform(min_s, max_s)
    return round(raw / 500) * 500


# ---------------------------------------------------------------------------
# Build everything in memory, then insert in FK-respecting order
# ---------------------------------------------------------------------------
def build_db(conn: sqlite3.Connection) -> None:
    conn.executescript(DDL)

    # ------------------------------------------------------------------
    # 1. Departments
    # ------------------------------------------------------------------
    dept_ids: list[int] = []
    for name, location, budget in DEPARTMENTS:
        cur = conn.execute(
            "INSERT INTO departments (name, location, budget) VALUES (?, ?, ?)",
            (name, location, budget),
        )
        dept_ids.append(cur.lastrowid)  # type: ignore[arg-type]

    # Map department name → id
    dept_name_to_id: dict[str, int] = {
        d[0]: dept_ids[i] for i, d in enumerate(DEPARTMENTS)
    }

    # ------------------------------------------------------------------
    # 2. Job titles
    # ------------------------------------------------------------------
    title_ids: list[int] = []
    for title, family, min_s, max_s in JOB_TITLES:
        cur = conn.execute(
            "INSERT INTO job_titles (title, job_family, min_salary, max_salary)"
            " VALUES (?, ?, ?, ?)",
            (title, family, min_s, max_s),
        )
        title_ids.append(cur.lastrowid)  # type: ignore[arg-type]

    # Map title text → (id, family, min_salary, max_salary)
    title_info: dict[str, tuple[int, str, float, float]] = {
        JOB_TITLES[i][0]: (title_ids[i], JOB_TITLES[i][1], JOB_TITLES[i][2], JOB_TITLES[i][3])
        for i in range(len(JOB_TITLES))
    }

    # Department → list of plausible job title texts
    dept_to_titles: dict[str, list[str]] = {
        "Engineering":      [t for t, f, _, _ in JOB_TITLES if f == "Engineering"],
        "Sales":            [t for t, f, _, _ in JOB_TITLES if f == "Sales"],
        "Marketing":        [t for t, f, _, _ in JOB_TITLES if f == "Marketing"],
        "Human Resources":  [t for t, f, _, _ in JOB_TITLES if f == "HR"],
        "Finance":          [t for t, f, _, _ in JOB_TITLES if f == "Finance"],
        "Customer Support": [t for t, f, _, _ in JOB_TITLES if f == "Support"],
        "Operations":       [t for t, f, _, _ in JOB_TITLES if f == "Operations"],
        "Legal":            [t for t, f, _, _ in JOB_TITLES if f == "Legal"],
    }

    # Department title weights — skew heavily toward IC contributor roles
    # so the org pyramid looks realistic (not all managers)
    # Weights mirror the position index within each dept list
    dept_title_weights: dict[str, list[float]] = {
        "Engineering":      [0.18, 0.30, 0.28, 0.12, 0.09, 0.03],
        "Sales":            [0.20, 0.30, 0.25, 0.18, 0.07],
        "Marketing":        [0.25, 0.35, 0.28, 0.12],
        "Human Resources":  [0.35, 0.45, 0.20],
        "Finance":          [0.30, 0.35, 0.25, 0.10],
        "Customer Support": [0.50, 0.30, 0.20],
        "Operations":       [0.45, 0.38, 0.17],
        "Legal":            [0.75, 0.25],
    }

    # ------------------------------------------------------------------
    # 3. Employees — two-pass to support self-referential manager_id
    #    Pass A: insert all without manager_id
    #    Pass B: UPDATE manager_id for non-executives
    # ------------------------------------------------------------------
    N_EMPLOYEES = 250
    hire_window_start = date(2018, 1, 2)
    hire_window_end = date(2024, 12, 31)

    dept_names = list(dept_name_to_id.keys())
    # Headcount weights — Engineering and Sales biggest
    dept_headcount_weights = [0.28, 0.22, 0.12, 0.08, 0.10, 0.08, 0.08, 0.04]

    # We'll track (employee_id, dept_name, title_text) to assign managers later
    employee_records: list[dict] = []
    used_emails: set[str] = set()

    for _ in range(N_EMPLOYEES):
        dept_name = random.choices(dept_names, weights=dept_headcount_weights, k=1)[0]
        dept_id = dept_name_to_id[dept_name]

        titles_for_dept = dept_to_titles[dept_name]
        weights_for_dept = dept_title_weights[dept_name]
        title_text = random.choices(titles_for_dept, weights=weights_for_dept, k=1)[0]
        job_title_id, _, min_s, max_s = title_info[title_text]

        hire_date = rand_date(hire_window_start, hire_window_end)
        # Birth date: age 22-60 at hire
        age_at_hire = random.randint(22, 60)
        birth_year = hire_date.year - age_at_hire
        birth_date = date(birth_year, random.randint(1, 12), random.randint(1, 28))

        gender = random.choices(GENDERS, weights=GENDER_WEIGHTS, k=1)[0]
        status = "active" if random.random() < 0.90 else "inactive"

        first = fake.first_name_male() if gender == "M" else fake.first_name_female()
        last = fake.last_name()
        base_email = f"{first.lower()}.{last.lower()}@example.com"
        # Deduplicate
        email = base_email
        suffix = 1
        while email in used_emails:
            email = f"{first.lower()}.{last.lower()}{suffix}@example.com"
            suffix += 1
        used_emails.add(email)

        phone = fake.numerify("###-###-####")
        city = fake.city()

        cur = conn.execute(
            """INSERT INTO employees
               (first_name, last_name, email, phone, hire_date, birth_date,
                gender, department_id, job_title_id, status, city, country)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (first, last, email, phone,
             hire_date.isoformat(), birth_date.isoformat(),
             gender, dept_id, job_title_id, status, city, "US"),
        )
        emp_id = cur.lastrowid
        employee_records.append({
            "employee_id": emp_id,
            "dept_name": dept_name,
            "title_text": title_text,
            "hire_date": hire_date,
        })

    # ------------------------------------------------------------------
    # Pass B — assign managers
    # For each department, collect employees whose title contains "Manager",
    # "Director", "VP", "Head", "CFO", "Counsel" (senior enough to manage),
    # then assign one as manager to everyone else in that dept.
    # ------------------------------------------------------------------
    senior_keywords = {"Manager", "Director", "VP", "Head", "CFO", "Counsel",
                       "Staff Engineer", "Engineering Manager", "VP of Engineering"}

    dept_managers: dict[str, list[int]] = {d: [] for d in dept_names}
    dept_ics: dict[str, list[dict]] = {d: [] for d in dept_names}

    for rec in employee_records:
        is_senior = any(kw in rec["title_text"] for kw in senior_keywords)
        if is_senior:
            dept_managers[rec["dept_name"]].append(rec["employee_id"])
        else:
            dept_ics[rec["dept_name"]].append(rec)

    for dept_name in dept_names:
        managers = dept_managers[dept_name]
        ics = dept_ics[dept_name]
        if not managers:
            # Promote the first IC to manager role for assignment purposes
            if ics:
                managers = [ics[0]["employee_id"]]
                ics = ics[1:]
        for ic_rec in ics:
            # Pick a manager who was hired before or on the same date (realistic)
            valid_managers = [
                m_id for m_id in managers
                if any(
                    r["employee_id"] == m_id and r["hire_date"] <= ic_rec["hire_date"]
                    for r in employee_records
                )
            ]
            chosen_manager = random.choice(valid_managers if valid_managers else managers)
            conn.execute(
                "UPDATE employees SET manager_id = ? WHERE employee_id = ?",
                (chosen_manager, ic_rec["employee_id"]),
            )

    # Build a flat list of all employee IDs for later FK references
    all_emp_ids: list[int] = [r["employee_id"] for r in employee_records]
    active_emp_ids: list[int] = [
        r["employee_id"] for r in employee_records
    ]

    # ------------------------------------------------------------------
    # 4. Salary history — 1 to 3 raises per employee
    # ------------------------------------------------------------------
    for rec in employee_records:
        emp_id = rec["employee_id"]
        hire_date = rec["hire_date"]
        title_text = rec["title_text"]
        _, _, min_s, max_s = title_info[title_text]

        # Starting salary at hire
        starting_salary = salary_in_band(min_s, min_s + (max_s - min_s) * 0.45)
        conn.execute(
            "INSERT INTO salary_history (employee_id, effective_from, salary, change_reason)"
            " VALUES (?, ?, ?, ?)",
            (emp_id, hire_date.isoformat(), starting_salary, "hire"),
        )

        # Subsequent raises (0 to 2 more)
        n_raises = random.choices([0, 1, 2], weights=[0.25, 0.50, 0.25], k=1)[0]
        last_salary = starting_salary
        last_date = hire_date

        for _ in range(n_raises):
            # Raises happen 6-24 months after the last event, but not in the future
            months_later = random.randint(12, 30)
            raise_date = last_date + timedelta(days=months_later * 30)
            if raise_date >= date.today():
                break
            reason = random.choice(CHANGE_REASONS)
            pct = random.uniform(0.03, 0.18)
            new_salary = round(last_salary * (1 + pct) / 500) * 500
            new_salary = min(new_salary, max_s * 1.05)  # cap slightly above band max
            conn.execute(
                "INSERT INTO salary_history (employee_id, effective_from, salary, change_reason)"
                " VALUES (?, ?, ?, ?)",
                (emp_id, raise_date.isoformat(), new_salary, reason),
            )
            last_salary = new_salary
            last_date = raise_date

    # ------------------------------------------------------------------
    # 5. Performance reviews — aim for ~150 total
    #    Each review needs a reviewer who is NOT the same person.
    # ------------------------------------------------------------------
    today = date.today()
    target_reviews = 150
    review_count = 0

    for rec in employee_records:
        emp_id = rec["employee_id"]
        hire_date = rec["hire_date"]

        # Number of annual review cycles this employee has been through
        years_employed = (today - hire_date).days / 365.25
        n_reviews = min(int(years_employed), 3)  # cap at 3 reviews per person
        if n_reviews == 0 and review_count < target_reviews:
            n_reviews = 1 if random.random() < 0.4 else 0

        review_year = hire_date.year
        for j in range(n_reviews):
            review_year = hire_date.year + j + 1
            if review_year > today.year:
                break
            period_start = date(review_year - 1, 1, 1)
            period_end = date(review_year - 1, 12, 31)
            # Review date: early in the following year
            review_date = date(review_year, random.randint(1, 3), random.randint(1, 28))
            if review_date > today:
                break

            # Reviewer: someone else in the org, ideally a manager
            other_ids = [i for i in all_emp_ids if i != emp_id]
            reviewer_id = random.choice(other_ids)

            rating = random.choices(REVIEW_RATINGS, weights=REVIEW_RATING_WEIGHTS, k=1)[0]
            comments = fake.sentence(nb_words=random.randint(8, 20))

            conn.execute(
                """INSERT INTO performance_reviews
                   (employee_id, reviewer_id, review_date, period_start, period_end,
                    rating, comments)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (emp_id, reviewer_id,
                 review_date.isoformat(), period_start.isoformat(), period_end.isoformat(),
                 rating, comments),
            )
            review_count += 1

    # ------------------------------------------------------------------
    # 6. Time-off requests — aim for ~120 rows
    # ------------------------------------------------------------------
    for _ in range(120):
        emp_rec = random.choice(employee_records)
        emp_id = emp_rec["employee_id"]
        hire_date = emp_rec["hire_date"]

        leave_type = random.choices(LEAVE_TYPES, weights=LEAVE_TYPE_WEIGHTS, k=1)[0]
        # Leave duration
        if leave_type == "parental":
            days = random.choice([42, 56, 84])
        elif leave_type == "sick":
            days = random.randint(1, 5)
        elif leave_type == "pto":
            days = random.randint(1, 15)
        else:  # unpaid
            days = random.randint(3, 20)

        # Start date must be after hire_date
        earliest = hire_date + timedelta(days=90)
        latest = today - timedelta(days=1)
        if earliest >= latest:
            continue
        start_date = rand_date(earliest, latest)
        end_date = start_date + timedelta(days=days - 1)
        if end_date > today:
            end_date = today

        lv_status = random.choices(LEAVE_STATUSES, weights=LEAVE_STATUS_WEIGHTS, k=1)[0]
        approved_by: int | None = None
        if lv_status == "approved":
            candidates = [i for i in all_emp_ids if i != emp_id]
            approved_by = random.choice(candidates)

        requested_on = start_date - timedelta(days=random.randint(3, 30))
        if requested_on < hire_date:
            requested_on = hire_date + timedelta(days=1)

        conn.execute(
            """INSERT INTO time_off_requests
               (employee_id, leave_type, start_date, end_date, days_requested,
                status, approved_by, requested_on)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (emp_id, leave_type,
             start_date.isoformat(), end_date.isoformat(), days,
             lv_status, approved_by, requested_on.isoformat()),
        )

    # ------------------------------------------------------------------
    # 7. Dependents — ~80 rows (only for employees who have them)
    # ------------------------------------------------------------------
    # Give ~45% of active employees at least one dependent
    emp_pool = active_emp_ids[:]
    random.shuffle(emp_pool)
    dep_employee_pool = emp_pool[: int(len(emp_pool) * 0.45)]

    dep_count = 0
    for emp_id in dep_employee_pool:
        emp_rec = next(r for r in employee_records if r["employee_id"] == emp_id)
        hire_date = emp_rec["hire_date"]

        n_deps = random.choices([1, 2, 3], weights=[0.55, 0.33, 0.12], k=1)[0]
        for _ in range(n_deps):
            relationship = random.choices(
                RELATIONSHIPS, weights=RELATIONSHIP_WEIGHTS, k=1
            )[0]
            if relationship in ("spouse", "domestic_partner"):
                birth_year = hire_date.year - random.randint(22, 55)
            elif relationship == "child":
                birth_year = hire_date.year - random.randint(0, 20)
            else:  # parent
                birth_year = hire_date.year - random.randint(45, 75)
            birth_date = date(birth_year, random.randint(1, 12), random.randint(1, 28))
            first = fake.first_name()
            last = fake.last_name()
            conn.execute(
                """INSERT INTO dependents
                   (employee_id, first_name, last_name, relationship, birth_date)
                   VALUES (?, ?, ?, ?, ?)""",
                (emp_id, first, last, relationship, birth_date.isoformat()),
            )
            dep_count += 1

    conn.commit()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    try:
        build_db(conn)
    finally:
        conn.close()

    # Row-count summary
    conn_r = sqlite3.connect(str(DB_PATH))
    tables = [
        "departments", "job_titles", "employees", "salary_history",
        "performance_reviews", "time_off_requests", "dependents",
    ]
    total = 0
    for t in tables:
        (n,) = conn_r.execute(f"SELECT COUNT(*) FROM {t}").fetchone()
        total += n
    conn_r.close()

    print(f"hr.db ready · {len(tables)} tables · {total} total rows")


if __name__ == "__main__":
    main()

"""
Grade boundary scraper and query module.

Scrapes historical grade boundaries from ibpredict.org and stores them in a
local SQLite database (grade_boundaries.db).

Usage:
  from grade_boundaries import grade_boundary_db
  grade_boundary_db.scrape_all()          # one-time / annual refresh
  grade_boundary_db.query(...)            # query boundaries
  grade_boundary_db.get_grade_for_score(...)  # score → IB grade
"""

import logging
import re
import sqlite3
import time
from typing import Dict, List, Optional, Tuple

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DB_PATH = "grade_boundaries.db"

# ibpredict.org slug → canonical subject name + levels
SUBJECTS_TO_SCRAPE = {
    "analysis-and-approaches":        ("Math AA",    ["HL", "SL"]),
    "applications-and-interpretation": ("Math AI",    ["HL", "SL"]),
    "physics":                         ("Physics",    ["HL", "SL"]),
    "chemistry":                       ("Chemistry",  ["HL", "SL"]),
    "biology":                         ("Biology",    ["HL", "SL"]),
    "economics":                       ("Economics",  ["HL", "SL"]),
    "computer-science":                ("Computer Science", ["HL", "SL"]),
}

IBPREDICT_BASE = "https://ibpredict.org/subjects/{slug}?lvl={level}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _parse_session_code(code: str) -> Optional[Tuple[int, str, str]]:
    """
    Parse ibpredict session codes into (year, session, timezone).

    Examples:
      "M25 TZ1"  → (2025, "May",      "TZ1")
      "N23 TZ2"  → (2023, "November", "TZ2")
      "N24 TZ0"  → (2024, "November", "TZ0")
    """
    m = re.match(r"^([MN])(\d{2})\s*(TZ\d+)$", code.strip(), re.IGNORECASE)
    if not m:
        return None
    month_code, year_2d, tz = m.groups()
    year = 2000 + int(year_2d)
    session = "May" if month_code.upper() == "M" else "November"
    return year, session, tz.upper()


# ---------------------------------------------------------------------------
# Database class
# ---------------------------------------------------------------------------

class GradeBoundaryDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    # ------------------------------------------------------------------
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS grade_boundaries (
                    subject  TEXT    NOT NULL,
                    level    TEXT    NOT NULL,
                    year     INTEGER NOT NULL,
                    session  TEXT    NOT NULL,
                    timezone TEXT    NOT NULL,
                    grade    INTEGER NOT NULL,
                    min_mark INTEGER NOT NULL,
                    PRIMARY KEY (subject, level, year, session, timezone, grade)
                )
            """)

    # ------------------------------------------------------------------
    def scrape_subject(self, subject_name: str, slug: str, level: str) -> int:
        """Scrape grade boundaries for one subject/level and store in DB."""
        url = IBPREDICT_BASE.format(slug=slug, level=level)
        logger.info(f"Scraping {url}")
        try:
            resp = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"HTTP error for {url}: {e}")
            return 0

        soup = BeautifulSoup(resp.text, "html.parser")
        tables = soup.find_all("table")
        rows_inserted = 0

        for table in tables:
            all_rows = table.find_all("tr")
            if len(all_rows) < 2:
                continue

            # Table layout on ibpredict.org:
            #   Row 0   = title cell spanning all columns (e.g. "HL Mathematics: ...")
            #   Row 1   = sub-headers: "Boundary*", "Markband (≥)", 1, 2, 3, 4, 5, 6, 7
            #   Rows 2+ = data rows, one per exam session
            #
            # Step 1 — scan the first few rows to find which one holds grade cols 1-7
            grade_cols: Dict[int, int] = {}  # col_index → grade (1-7)
            header_row_idx = 0
            for scan_idx in range(min(3, len(all_rows))):
                cells = all_rows[scan_idx].find_all(["th", "td"])
                candidate: Dict[int, int] = {}
                for i, cell in enumerate(cells):
                    text = cell.get_text(strip=True)
                    if re.match(r"^([1-7])$", text):
                        candidate[i] = int(text)
                if candidate:
                    grade_cols = candidate
                    header_row_idx = scan_idx
                    break

            if not grade_cols:
                continue  # Not a grade boundary table

            # Detect actual level from the table title (row 0).
            # ibpredict shows both HL and SL tables on the same page, so we
            # can't rely on the `level` argument — use the title instead.
            title_text = all_rows[0].get_text(strip=True).upper()
            if title_text.startswith("HL"):
                actual_level = "HL"
            elif title_text.startswith("SL"):
                actual_level = "SL"
            else:
                actual_level = level  # fallback

            # "Boundary*" uses rowspan=2, so it doesn't appear in the grade-number
            # header row — meaning grade "1" lands at col index 0 in that row, but
            # data rows have the session code at col 0 and marks starting at col 1.
            # Detect this by checking if the first cell of the header row is itself
            # a grade digit, and if so shift all indices by +1.
            header_cells_check = all_rows[header_row_idx].find_all(["th", "td"])
            if header_cells_check and re.match(r"^[1-7]$", header_cells_check[0].get_text(strip=True)):
                grade_cols = {col + 1: grade for col, grade in grade_cols.items()}

            # Step 2 — each data row is one session
            for row in all_rows[header_row_idx + 1:]:
                cells = row.find_all(["td", "th"])
                if not cells:
                    continue
                # First cell is the session code e.g. "N25 TZ3"
                session_text = cells[0].get_text(strip=True)
                parsed = _parse_session_code(session_text)
                if not parsed:
                    continue
                year, session, tz = parsed

                with sqlite3.connect(self.db_path) as conn:
                    for col_idx, grade in grade_cols.items():
                        if col_idx >= len(cells):
                            continue
                        mark_text = cells[col_idx].get_text(strip=True).replace(",", "")
                        try:
                            min_mark = int(mark_text)
                        except ValueError:
                            continue
                        conn.execute("""
                            INSERT OR REPLACE INTO grade_boundaries
                            (subject, level, year, session, timezone, grade, min_mark)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (subject_name, actual_level, year, session, tz, grade, min_mark))
                        rows_inserted += 1

        logger.info(f"  → {rows_inserted} rows stored for {subject_name} {level}")
        return rows_inserted

    # ------------------------------------------------------------------
    def scrape_all(self) -> int:
        """Scrape all configured subjects. Polite 1-second delay between requests."""
        total = 0
        for slug, (subject_name, levels) in SUBJECTS_TO_SCRAPE.items():
            for level in levels:
                total += self.scrape_subject(subject_name, slug, level)
                time.sleep(1)  # be polite
        logger.info(f"Grade boundary scrape complete — {total} rows total.")
        return total

    # ------------------------------------------------------------------
    def query(
        self,
        subject: str,
        level: str,
        year: int,
        session: str,
        timezone: Optional[str] = None,
    ) -> List[Dict]:
        """
        Return grade boundaries as a list of dicts.

        If timezone is given, returns one row per grade for that timezone.
        If timezone is None, returns rows for all timezones grouped.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if timezone:
                # Normalise: TZ0 is sometimes used for November global
                rows = conn.execute("""
                    SELECT grade, min_mark FROM grade_boundaries
                    WHERE subject=? AND level=? AND year=? AND session=? AND timezone=?
                    ORDER BY grade DESC
                """, (subject, level, year, session, timezone.upper())).fetchall()
            else:
                rows = conn.execute("""
                    SELECT timezone, grade, min_mark FROM grade_boundaries
                    WHERE subject=? AND level=? AND year=? AND session=?
                    ORDER BY timezone, grade DESC
                """, (subject, level, year, session)).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    def get_grade_for_score(
        self,
        subject: str,
        level: str,
        year: int,
        session: str,
        timezone: str,
        score: int,
    ) -> Optional[int]:
        """Return the IB grade (1-7) for a given raw composite score."""
        rows = self.query(subject, level, year, session, timezone)
        # rows are sorted grade DESC; find highest grade whose min_mark <= score
        for row in sorted(rows, key=lambda r: r["min_mark"], reverse=True):
            if score >= row["min_mark"]:
                return row["grade"]
        return 1

    # ------------------------------------------------------------------
    def has_data(self, subject: str, level: str) -> bool:
        """Return True if we have any data for this subject/level."""
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM grade_boundaries WHERE subject=? AND level=?",
                (subject, level)
            ).fetchone()[0]
        return count > 0

    # ------------------------------------------------------------------
    def available_sessions(self, subject: str, level: str) -> List[str]:
        """Return list of 'May YYYY TZ1' style strings for a subject/level."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT DISTINCT year, session, timezone FROM grade_boundaries
                WHERE subject=? AND level=?
                ORDER BY year DESC, session, timezone
            """, (subject, level)).fetchall()
        return [f"{s} {y} {tz}" for y, s, tz in rows]

    # ------------------------------------------------------------------
    def row_count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM grade_boundaries").fetchone()[0]


# Singleton
grade_boundary_db = GradeBoundaryDB()

"""
Tracks user logins in SQLite for admin review.
"""

import sqlite3
from datetime import datetime, timezone

DB_PATH = "logins.db"


class LoginTracker:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS logins (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    email       TEXT NOT NULL,
                    name        TEXT,
                    picture     TEXT,
                    ip_address  TEXT,
                    logged_in_at TEXT NOT NULL
                )
            """)

    def record(self, email: str, name: str, picture: str = None, ip_address: str = None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO logins (email, name, picture, ip_address, logged_in_at) VALUES (?, ?, ?, ?, ?)",
                (email, name, picture, ip_address, datetime.now(timezone.utc).isoformat()),
            )

    def get_all(self, limit: int = 500) -> list:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM logins ORDER BY logged_in_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_unique_users(self) -> list:
        """Most recent login per unique email."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT email, name, picture, ip_address, MAX(logged_in_at) as last_seen, COUNT(*) as login_count
                FROM logins
                GROUP BY email
                ORDER BY last_seen DESC
            """).fetchall()
        return [dict(r) for r in rows]

    def total_count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM logins").fetchone()[0]


login_tracker = LoginTracker()

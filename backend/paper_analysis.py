"""
Paper analysis module.

Stores per-paper AI analysis (topics, question breakdown, difficulty) in SQLite.
Run analyze_papers.py once to populate; re-run after adding new papers.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DB_PATH = "paper_analyses.db"

ANALYSIS_PROMPT = """\
You are an expert IB examiner analysing a past paper question paper.
Extract structured data and return ONLY a valid JSON object (no markdown, no explanation):

{{
  "difficulty": "Easy" | "Medium" | "Hard",
  "topics": ["topic1", "topic2"],
  "questions": [
    {{
      "num": <integer>,
      "section": "A" | "B" | null,
      "marks": <integer or null>,
      "topic": "<IB syllabus topic>",
      "subtopic": "<specific concept>"
    }}
  ]
}}

Rules:
- topics: official IB topic names only, e.g. "Calculus", "Statistics & Probability", "Complex Numbers", "Functions", "Vectors", "Algebra", "Geometry & Trigonometry", "Number & Algebra", "Differential Equations"
- Section A = short questions, Section B = long structured questions. If no clear sections, use null.
- difficulty: Easy = mostly routine, Medium = mix, Hard = several challenging Section B questions
- subtopic should be specific: e.g. "Integration by substitution", "Binomial theorem", "De Moivre's theorem", "Normal distribution"

Paper content:
{text}
"""


class PaperAnalysisDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS paper_analyses (
                    file_id        TEXT PRIMARY KEY,
                    subject        TEXT,
                    level          TEXT,
                    year           INTEGER,
                    session        TEXT,
                    timezone       TEXT,
                    paper          INTEGER,
                    difficulty     TEXT,
                    topics         TEXT,
                    questions_json TEXT,
                    analyzed_at    TEXT
                )
            """)

    def store(self, file_id: str, metadata: dict, analysis: dict):
        topics_str = ",".join(analysis.get("topics", []))
        questions_json = json.dumps(analysis.get("questions", []))
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO paper_analyses
                (file_id, subject, level, year, session, timezone, paper,
                 difficulty, topics, questions_json, analyzed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_id,
                metadata.get("subject"),
                metadata.get("level"),
                metadata.get("year"),
                metadata.get("session"),
                metadata.get("timezone"),
                metadata.get("paper"),
                analysis.get("difficulty"),
                topics_str,
                questions_json,
                datetime.now(timezone.utc).isoformat(),
            ))

    def is_analyzed(self, file_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM paper_analyses WHERE file_id=?", (file_id,)
            ).fetchone()
        return row is not None

    def get(self, file_id: str) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM paper_analyses WHERE file_id=?", (file_id,)
            ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["topics"] = [t for t in d["topics"].split(",") if t] if d["topics"] else []
        questions = json.loads(d["questions_json"] or "[]")
        d["questions"] = questions
        # Derive Section B topics from stored questions
        seen = set()
        section_b_topics = []
        for q in questions:
            if (q.get("section") or "").upper() == "B":
                t = q.get("subtopic") or q.get("topic") or ""
                if t and t not in seen:
                    seen.add(t)
                    section_b_topics.append(t)
        d["section_b_topics"] = section_b_topics
        del d["questions_json"]
        return d

    def search(
        self,
        topic: str,
        subject: Optional[str] = None,
        level: Optional[str] = None,
        section: Optional[str] = None,
    ) -> List[str]:
        """Return file_ids whose analysis matches the topic/section query."""
        like = f"%{topic}%"
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT file_id, subject, level, questions_json, topics
                FROM paper_analyses
                WHERE topics LIKE ? OR questions_json LIKE ?
            """, (like, like)).fetchall()

        results = []
        for row in rows:
            if subject and (row["subject"] or "").lower() != subject.lower():
                continue
            if level and (row["level"] or "").upper() != level.upper():
                continue
            if section:
                questions = json.loads(row["questions_json"] or "[]")
                hit = any(
                    (q.get("section") or "").upper() == section.upper()
                    and topic.lower() in (
                        (q.get("topic") or "") + " " + (q.get("subtopic") or "")
                    ).lower()
                    for q in questions
                )
                if not hit:
                    continue
            results.append(row["file_id"])
        return results

    def count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM paper_analyses").fetchone()[0]


paper_analysis_db = PaperAnalysisDB()

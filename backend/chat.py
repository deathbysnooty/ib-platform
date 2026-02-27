"""
Claude API integration.

Two jobs:
1. parse_query()    — extract structured search params from a student's natural-language message
2. summarize_paper() — produce a question-by-question breakdown of a paper
"""

import json
import logging
from typing import List, Optional

import anthropic

from models import ParsedQuery, PaperGroup
from grade_boundaries import grade_boundary_db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

PARSE_PROMPT = """\
You help students find IB past papers. Extract search parameters from the student's message.

Student message: {message}

Return ONLY a JSON object with these fields (use null when not mentioned):
{{
  "subject": "Math AA" | "Math AI" | "Physics" | "Chemistry" | "Biology" | "Economics" | "Computer Science" | "History" | "Geography" | "Psychology" | "English A Lit" | "English A Lang&Lit" | "English B" | "Business Management" | "ESS" | "Global Politics" | null,
  "level": "HL" | "SL" | null,
  "year": integer | null,
  "session": "May" | "November" | "Specimen" | null,
  "paper": 1 | 2 | 3 | null,
  "timezone": "TZ1" | "TZ2" | "TZ3" | null,
  "resource_type": "data_booklet" | "grade_boundary" | "topic_search" | null,
  "score": integer | null,
  "topic_query": string | null,
  "section": "A" | "B" | null
}}

Rules:
- "Math AA" = Mathematics Analysis and Approaches
- "Math AI" = Mathematics Applications and Interpretation
- If student says "Maths" treat as Math AA unless they say AI/Applications
- Before 2021 there was no Math AI — the old "Math SL" and "Math HL" curricula align with Math AA. So if the student says "Math HL" or "Math SL" without mentioning AA/AI, treat as "Math AA".
- Math AI only exists from 2021 onwards. If a student asks for Math AI before 2021, still return subject="Math AI" (no results will be found and that's correct).
- "Specimen" papers are official IB sample papers released when a new syllabus launched. If the student asks for "specimen paper", set session="Specimen".
- If the student asks for "data booklet", "formula booklet", "formula sheet", or "formula book", set resource_type="data_booklet" (and subject/level if mentioned).
- If the student asks about "grade boundaries", "grade boundary", "what grade is X marks", "what do I need for a 7", "pass mark", set resource_type="grade_boundary". Also extract score if they say things like "I got 65 marks" or "what grade is 72/100".
- If the student asks about specific topics, question types, or difficulty (e.g. "papers with complex numbers", "Section B on integration", "which papers have vectors", "long answer questions on calculus", "hard questions on statistics"), set resource_type="topic_search", topic_query=the topic/concept (e.g. "complex numbers", "integration", "vectors"), and section="B" if they say "Section B" or "long answer".
- Return ONLY the JSON object, no markdown or explanation.
"""

SUMMARIZE_PROMPT = """\
You are an expert IB examiner. Analyse this exam paper and produce a topic breakdown for students.

List each IB syllabus topic that appears in this paper with:
- The approximate percentage of marks it accounts for
- A one-line note on what was asked

Format like this:
**Topic Name** — X%
One sentence describing what was tested.

Then add a short 2-3 line overall note on difficulty and the most important topics to revise.

Paper content:
{text}
"""


class ChatHandler:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    # ------------------------------------------------------------------
    def parse_query(self, message: str) -> ParsedQuery:
        """Use Claude Haiku (cheap + fast) to extract search params."""
        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=400,
                messages=[{"role": "user", "content": PARSE_PROMPT.format(message=message)}],
            )
            raw = response.content[0].text.strip()
            # Strip markdown code fences if present
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            return ParsedQuery(**{k: v for k, v in data.items() if v is not None})
        except Exception as e:
            logger.error(f"parse_query error: {e}")
            return ParsedQuery()

    # ------------------------------------------------------------------
    def build_response_message(self, query: ParsedQuery, groups: List[PaperGroup]) -> str:
        if not groups:
            parts = list(filter(None, [query.subject, query.level, query.session, str(query.year) if query.year else None]))
            desc = " ".join(parts) if parts else "those papers"
            return (
                f"I couldn't find any papers matching **{desc}**. "
                "Please double-check the subject name, year, or session and try again. "
                'You can ask something like: *"Math AA HL May 2024 Paper 2"*.'
            )

        tz_list = ", ".join(sorted({g.timezone for g in groups}))
        subject = groups[0].subject
        level = groups[0].level or ""
        session = groups[0].session or ""
        year = str(groups[0].year) if groups[0].year else ""
        papers = sorted({g.paper for g in groups if g.paper})
        paper_str = f" Paper {', '.join(map(str, papers))}" if papers else ""

        return (
            f"Here are the **{subject} {level} {session} {year}{paper_str}** papers "
            f"({tz_list}). Each card has the Question Paper and Markscheme. "
            f"Click **AI Summary** on any question paper to get a question-by-question breakdown."
        )

    # ------------------------------------------------------------------
    def build_topic_search_response(self, query: ParsedQuery, groups: List[PaperGroup]) -> str:
        topic = query.topic_query or ""
        section_str = f" Section {query.section}" if query.section else ""
        subject_str = f"{query.subject} {query.level}".strip() if query.subject else "Math AA/AI"

        if not groups:
            return (
                f"No papers found with{section_str} questions on **{topic}** for **{subject_str}**. "
                "The topic may not appear in the analysed papers, or try rephrasing (e.g. \"complex numbers\", \"integration\", \"vectors\")."
            )

        return (
            f"Found **{len(groups)}** paper(s) with{section_str} questions on **{topic}**"
            f"{' for ' + subject_str if subject_str else ''}. "
            "Topic tags are shown on each card."
        )

    # ------------------------------------------------------------------
    def build_grade_boundary_response(self, query: ParsedQuery) -> str:
        subject = query.subject
        level = query.level
        year = query.year
        session = query.session
        timezone = query.timezone
        score = query.score

        if not subject or not level:
            return (
                "Please specify a subject and level, e.g. "
                "*\"grade boundaries Math AA HL May 2023\"*."
            )
        if not year or not session:
            # Show what sessions are available
            sessions = grade_boundary_db.available_sessions(subject, level)
            if not sessions:
                return (
                    f"I don't have grade boundary data for **{subject} {level}** yet. "
                    "Ask an admin to run the grade boundary scraper."
                )
            sessions_str = ", ".join(sessions[:10])
            return (
                f"I have grade boundaries for **{subject} {level}** in these sessions: "
                f"{sessions_str}.\n\nTry: *\"{subject} {level} May 2023 grade boundaries\"*"
            )

        rows = grade_boundary_db.query(subject, level, year, session, timezone)
        if not rows:
            return (
                f"No grade boundary data found for **{subject} {level} {session} {year}"
                f"{' ' + timezone if timezone else ''}**. "
                "Data may not have been scraped yet, or this session doesn't exist."
            )

        label = f"{subject} {level} {session} {year}{' ' + timezone if timezone else ''}"

        # If user gave a score, return their grade
        if score is not None and timezone:
            grade = grade_boundary_db.get_grade_for_score(subject, level, year, session, timezone, score)
            sorted_rows = sorted(rows, key=lambda r: r["min_mark"], reverse=True)
            grade7_mark = next((r["min_mark"] for r in sorted_rows if r["grade"] == 7), "?")
            return (
                f"**{score}/100** in **{label}** → **Grade {grade}**\n\n"
                f"Grade 7 boundary was **{grade7_mark}** for this session."
            )

        # No timezone specified — group by timezone
        if not timezone:
            tz_groups: dict = {}
            for row in rows:
                tz = row.get("timezone", "?")
                tz_groups.setdefault(tz, {})[row["grade"]] = row["min_mark"]

            lines = [f"**{label} Grade Boundaries**\n"]
            tzs = sorted(tz_groups.keys())
            header = "| Grade | " + " | ".join(tzs) + " |"
            sep = "|-------|" + "|".join(["------"] * len(tzs)) + "|"
            lines.append(header)
            lines.append(sep)
            for g in range(7, 0, -1):
                marks = " | ".join(str(tz_groups[tz].get(g, "—")) for tz in tzs)
                lines.append(f"| **{g}**   | {marks} |")
            lines.append("\n*Minimum mark out of 100 to achieve each grade.*")
            if score is not None:
                lines.append(f"\n*You scored {score} — specify a timezone (TZ1/TZ2/TZ3) to get your exact grade.*")
            return "\n".join(lines)

        # Single timezone table
        sorted_rows = sorted(rows, key=lambda r: r["grade"], reverse=True)
        lines = [
            f"**{label} Grade Boundaries**\n",
            "| Grade | Min Mark |",
            "|-------|----------|",
        ]
        for row in sorted_rows:
            lines.append(f"| **{row['grade']}**   | {row['min_mark']}       |")
        lines.append("\n*Minimum mark out of 100 to achieve each grade.*")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    def build_resource_response(self, query: ParsedQuery, files: List) -> str:
        if not files:
            parts = list(filter(None, [query.subject, query.level]))
            desc = " ".join(parts) if parts else "that subject"
            return (
                f"I couldn't find a data booklet for **{desc}**. "
                "Try asking for a specific subject, e.g. *\"Math AA data booklet\"*."
            )
        subject = files[0].subject or "IB"
        level = files[0].level or ""
        label = f"{subject} {level}".strip()
        return (
            f"Here is the **{label} Data Booklet / Formula Booklet** — "
            "provided by IB and used in all exams for this subject."
        )

    # ------------------------------------------------------------------
    def summarize_paper(self, pdf_text: str) -> str:
        if not pdf_text.strip():
            return (
                "Sorry, I wasn't able to extract text from this PDF — it may be a scanned image. "
                "Try a different paper or ask your teacher for a text-based version."
            )
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2500,
                messages=[{"role": "user", "content": SUMMARIZE_PROMPT.format(text=pdf_text)}],
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"summarize_paper error: {e}")
            return "An error occurred while generating the summary. Please try again."

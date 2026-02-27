"""
One-time deep analysis script for Math AA and Math AI question papers.

Run from backend/ directory:
    python3 analyze_papers.py

Analyses question papers (NOT markschemes) for:
  - Math AA HL + SL
  - Math AI HL + SL
  - Session = Specimen OR year >= 2021

Skips papers already in the DB. Safe to re-run after adding new papers.
"""

import json
import logging
import os
import time

from dotenv import load_dotenv
load_dotenv()

import anthropic
from drive import drive_index
from paper_analysis import ANALYSIS_PROMPT, paper_analysis_db

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

MATH_SUBJECTS = {"math aa", "math ai"}


def main():
    root_id = os.environ["DRIVE_ROOT_FOLDER_ID"]
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    sa_info = json.loads(sa_json) if sa_json else None
    drive_index.initialize(root_id, service_account_info=sa_info)

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    candidates = [
        p for p in drive_index.papers
        if p.type == "question"
        and (p.subject or "").lower() in MATH_SUBJECTS
        and (p.session == "Specimen" or (p.year is not None and p.year >= 2021))
    ]

    logger.info(f"Found {len(candidates)} papers to analyse (Math AA + AI, 2021+/Specimen, question only).")

    skipped = done = failed = 0

    for paper in candidates:
        if paper_analysis_db.is_analyzed(paper.file_id):
            skipped += 1
            continue

        label = f"{paper.subject} {paper.level} {paper.session} {paper.year} P{paper.paper} {paper.timezone or ''}"
        logger.info(f"Analysing: {label}")

        try:
            text = drive_index.get_text_from_pdf(paper.file_id)
            if not text.strip():
                logger.warning("  → No text extracted (scanned PDF?), skipping.")
                failed += 1
                continue

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1500,
                messages=[{"role": "user", "content": ANALYSIS_PROMPT.format(text=text[:40000])}],
            )
            raw = response.content[0].text.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            analysis = json.loads(raw)
            paper_analysis_db.store(
                paper.file_id,
                {
                    "subject": paper.subject,
                    "level": paper.level,
                    "year": paper.year,
                    "session": paper.session,
                    "timezone": paper.timezone,
                    "paper": paper.paper,
                },
                analysis,
            )
            logger.info(f"  → difficulty={analysis.get('difficulty')}, topics={analysis.get('topics')}")
            done += 1
            time.sleep(0.5)

        except Exception as e:
            logger.error(f"  → Error: {e}")
            failed += 1

    logger.info(f"\nDone. Analysed={done}, Skipped(already done)={skipped}, Failed={failed}")
    logger.info(f"Total in DB: {paper_analysis_db.count()}")


if __name__ == "__main__":
    main()

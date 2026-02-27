"""
Google Drive integration.

Supports two authentication methods — whichever env vars are present is used:

  Method A — OAuth refresh token (use this if service account keys are blocked):
    GOOGLE_REFRESH_TOKEN + GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET
    Run  python get_refresh_token.py  once to generate these values.

  Method B — Service account JSON key (if your org allows it):
    GOOGLE_SERVICE_ACCOUNT_JSON

Walks the folder tree, parses folder/file names into structured metadata, and
builds an in-memory index that the chat handler can search.
"""

import io
import os
import re
import logging
from typing import List, Optional, Dict, Tuple

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

from models import PaperFile, PaperGroup

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# ---------------------------------------------------------------------------
# Subject normalisation
# ---------------------------------------------------------------------------

SUBJECT_NORMALIZATION = {
    "mathematics analysis and approaches": "Math AA",
    "mathematics_analysis_and_approaches": "Math AA",
    "math aa": "Math AA",
    "maths aa": "Math AA",
    "paper aa": "Math AA",   # matches "Specimen Paper AA" after token removal
    "mathematics applications and interpretation": "Math AI",
    "mathematics_applications_and_interpretation": "Math AI",
    "math ai": "Math AI",
    "maths ai": "Math AI",
    "paper ai": "Math AI",   # matches "Specimen Paper AI" after token removal
    "physics": "Physics",
    "chemistry": "Chemistry",
    "biology": "Biology",
    "computer science": "Computer Science",
    "economics": "Economics",
    "history": "History",
    "geography": "Geography",
    "psychology": "Psychology",
    "english a literature": "English A Lit",
    "english a language and literature": "English A Lang&Lit",
    "english b": "English B",
    "business management": "Business Management",
    "environmental systems and societies": "ESS",
    "global politics": "Global Politics",
}


def normalize_subject(raw: str) -> str:
    cleaned = raw.lower().strip()
    cleaned = re.sub(r"[_\-]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    for pattern, canonical in SUBJECT_NORMALIZATION.items():
        if pattern in cleaned:
            return canonical
    return raw.strip().title()


def subject_matches(file_subject: Optional[str], query_subject: str) -> bool:
    if not file_subject:
        return False
    nf = normalize_subject(file_subject).lower()
    nq = query_subject.lower()
    if nf == nq:
        return True
    if nq in nf or nf in nq:
        return True
    # Handle shorthand aliases
    aliases: Dict[str, List[str]] = {
        "math aa": ["math aa", "maths aa", "mathematics aa", "mathematics analysis", "analysis and approaches", "analysis_and_approaches", "math hl", "math sl", "maths hl", "maths sl", "mathematics hl", "mathematics sl"],
        "math ai": ["math ai", "maths ai", "mathematics ai", "mathematics applications", "applications and interpretation", "applications_and_interpretation"],
        "physics": ["physics"],
        "chemistry": ["chemistry", "chem"],
        "biology": ["bio", "biology"],
        "economics": ["economics", "econ"],
        "computer science": ["computer science", "cs"],
    }
    for key, variants in aliases.items():
        if any(v in nq for v in variants) and any(v in nf for v in variants):
            return True
    return False


# ---------------------------------------------------------------------------
# Folder / filename parsing
# ---------------------------------------------------------------------------

def parse_folder_name(name: str) -> dict:
    """
    Parse folder names such as '2025 May Math AA HL' into metadata dict.
    """
    meta: dict = {}

    year_m = re.search(r"\b(20\d{2})\b", name)
    if year_m:
        meta["year"] = int(year_m.group(1))

    if re.search(r"\bSpecimen\b", name, re.IGNORECASE):
        meta["session"] = "Specimen"
    elif re.search(r"\bMay\b", name, re.IGNORECASE):
        meta["session"] = "May"
    elif re.search(r"\b(November|Nov)\b", name, re.IGNORECASE):
        meta["session"] = "November"
    elif re.search(r"\b(October|Oct)\b", name, re.IGNORECASE):
        meta["session"] = "October"

    # Data booklet folders — tag all files inside as data_booklet
    if re.search(r"data.?booklet|formula.?booklet|formula.?sheet", name, re.IGNORECASE):
        meta["type"] = "data_booklet"

    level_m = re.search(r"\b(HL|SL)\b", name, re.IGNORECASE)
    if level_m:
        meta["level"] = level_m.group(1).upper()

    # Subject = folder name minus the tokens we already extracted
    subject = name
    subject = re.sub(r"\b20\d{2}\b", "", subject)
    subject = re.sub(r"\b(May|November|Nov|October|Oct|Specimen)\b", "", subject, flags=re.IGNORECASE)
    subject = re.sub(r"\b(HL|SL)\b", "", subject, flags=re.IGNORECASE)
    subject = re.sub(r"\b(papers?)\b", "", subject, flags=re.IGNORECASE)  # strip generic word "papers"
    subject = " ".join(subject.split())
    if subject:
        meta["subject"] = normalize_subject(subject)

    return meta


def parse_filename(name: str) -> dict:
    """
    Parse file names such as:
      'Mathematics_analysis_and_approaches_paper_2__TZ1_HL.pdf'
      'Mathematics_applications_paper_1_TZ2_SL_markscheme.pdf'
    """
    meta: dict = {}
    stem = re.sub(r"\.pdf$", "", name, flags=re.IGNORECASE).lower()

    # Type: data booklet, markscheme, or question paper
    if re.search(r"data.?booklet|formula.?booklet|formula.?sheet", stem):
        meta["type"] = "data_booklet"
    elif "markscheme" in stem or re.search(r"[_\s]ms[_\s.]", stem) or stem.endswith("_ms"):
        meta["type"] = "markscheme"
    else:
        meta["type"] = "question"

    # Paper number
    paper_m = re.search(r"paper[_\s]?(\d)", stem)
    if paper_m:
        meta["paper"] = int(paper_m.group(1))

    # Timezone
    tz_m = re.search(r"(tz[123])", stem, re.IGNORECASE)
    if tz_m:
        meta["timezone"] = tz_m.group(1).upper()

    # Level (may be set by folder already; filename overrides if found)
    # Use [_\s\-] to handle tokens like "_HL" where underscore breaks \b
    level_m = re.search(r"[_\s\-](hl|sl)([_\s\-.]|$)", stem)
    if level_m:
        meta["level"] = level_m.group(1).upper()

    # Subject from filename (overrides folder if present)
    if "analysis_and_approaches" in stem or "analysis and approaches" in stem:
        meta["subject"] = "Math AA"
    elif "applications_and_interpretation" in stem or "applications and interpretation" in stem:
        meta["subject"] = "Math AI"

    return meta


# ---------------------------------------------------------------------------
# Drive index
# ---------------------------------------------------------------------------

class DriveIndex:
    def __init__(self):
        self.papers: List[PaperFile] = []
        self.service = None
        self._root_folder_id: Optional[str] = None
        self.ready = False

    def initialize(self, root_folder_id: str, service_account_info: Optional[dict] = None):
        """
        Authenticate with Drive and build the index.

        Prefers OAuth refresh token if GOOGLE_REFRESH_TOKEN is set,
        otherwise falls back to the service account JSON.
        """
        refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN")
        client_id     = os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

        if refresh_token and client_id and client_secret:
            logger.info("Authenticating with OAuth refresh token …")
            creds = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
            )
            # Force a token refresh so we catch bad credentials early
            creds.refresh(Request())
        elif service_account_info:
            logger.info("Authenticating with service account …")
            creds = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=SCOPES
            )
        else:
            raise RuntimeError(
                "No Drive credentials found. Set either GOOGLE_REFRESH_TOKEN "
                "(+ GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET) or GOOGLE_SERVICE_ACCOUNT_JSON."
            )

        self.service = build("drive", "v3", credentials=creds)
        self._root_folder_id = root_folder_id
        self.refresh(root_folder_id)
        self.ready = True

    def refresh(self, root_folder_id: str):
        logger.info("Building Drive index …")
        self.papers = []
        self._walk_folder(root_folder_id, {}, depth=0)
        logger.info(f"Index complete — {len(self.papers)} files indexed.")

    # ------------------------------------------------------------------
    def _list_folder(self, folder_id: str) -> list:
        items = []
        page_token = None
        while True:
            params = {
                "q": f"'{folder_id}' in parents and trashed=false",
                "fields": "nextPageToken, files(id, name, mimeType)",
                "pageSize": 1000,
            }
            if page_token:
                params["pageToken"] = page_token
            result = self.service.files().list(**params).execute()
            items.extend(result.get("files", []))
            page_token = result.get("nextPageToken")
            if not page_token:
                break
        return items

    def _walk_folder(self, folder_id: str, inherited_meta: dict, depth: int):
        if depth > 6:
            return
        try:
            items = self._list_folder(folder_id)
        except HttpError as e:
            logger.error(f"Drive error listing {folder_id}: {e}")
            return

        for item in items:
            if item["mimeType"] == "application/vnd.google-apps.folder":
                folder_meta = parse_folder_name(item["name"])
                merged = {**inherited_meta, **{k: v for k, v in folder_meta.items() if v is not None}}
                self._walk_folder(item["id"], merged, depth + 1)

            elif item["name"].lower().endswith(".pdf"):
                file_meta = parse_filename(item["name"])
                merged = {**inherited_meta, **{k: v for k, v in file_meta.items() if v is not None}}
                paper = PaperFile(
                    file_id=item["id"],
                    filename=item["name"],
                    subject=merged.get("subject"),
                    level=merged.get("level"),
                    year=merged.get("year"),
                    session=merged.get("session"),
                    paper=merged.get("paper"),
                    timezone=merged.get("timezone"),
                    type=merged.get("type", "question"),
                    folder_path=merged.get("folder_name", ""),
                )
                self.papers.append(paper)

    # ------------------------------------------------------------------
    def search(
        self,
        subject: Optional[str] = None,
        level: Optional[str] = None,
        year: Optional[int] = None,
        session: Optional[str] = None,
        paper: Optional[int] = None,
        timezone: Optional[str] = None,
        resource_type: Optional[str] = None,
    ) -> List[PaperFile]:
        if resource_type:
            results = [f for f in self.papers if f.type == resource_type]
        else:
            # Normal paper search — exclude data booklets
            results = [f for f in self.papers if f.type != "data_booklet"]
        if subject:
            results = [f for f in results if subject_matches(f.subject, subject)]
        if level:
            results = [f for f in results if f.level and f.level.upper() == level.upper()]
        if year:
            results = [f for f in results if f.year == year]
        if session:
            results = [f for f in results if f.session and f.session.lower() == session.lower()]
        if paper:
            results = [f for f in results if f.paper == paper]
        if timezone:
            results = [f for f in results if f.timezone and f.timezone.upper() == timezone.upper()]
        return results

    def group_results(self, files: List[PaperFile]) -> List[PaperGroup]:
        """Pair question papers with their markschemes by (subject, level, year, session, paper, TZ)."""
        groups: Dict[tuple, PaperGroup] = {}
        for f in files:
            key = (
                f.subject or "",
                f.level or "",
                f.year or 0,
                f.session or "",
                f.paper or 0,
                f.timezone or "unknown",
            )
            if key not in groups:
                groups[key] = PaperGroup(
                    subject=f.subject or "Unknown",
                    level=f.level,
                    year=f.year,
                    session=f.session,
                    paper=f.paper,
                    timezone=f.timezone or "unknown",
                )
            if f.type == "markscheme":
                groups[key].markscheme = f
            else:
                groups[key].question_paper = f

        return sorted(groups.values(), key=lambda g: (g.paper or 0, g.timezone))

    # ------------------------------------------------------------------
    def get_paper_by_id(self, file_id: str) -> Optional["PaperFile"]:
        for p in self.papers:
            if p.file_id == file_id:
                return p
        return None

    def get_file_bytes(self, file_id: str) -> Tuple[bytes, str]:
        file_meta = self.service.files().get(fileId=file_id, fields="name").execute()
        filename = file_meta.get("name", "paper.pdf")
        request = self.service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return fh.getvalue(), filename

    def get_text_from_pdf(self, file_id: str) -> str:
        pdf_bytes, _ = self.get_file_bytes(file_id)
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
            return text[:50000]  # cap at 50 k chars to stay within Claude's context
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return ""


# Singleton used by main.py
drive_index = DriveIndex()

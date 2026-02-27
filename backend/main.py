"""
FastAPI application entry point.

Routes:
  POST /api/auth/google          — exchange Google ID token for session cookie
  POST /api/auth/logout          — clear session cookie
  GET  /api/auth/me              — return current user
  POST /api/chat                 — natural-language paper search
  GET  /api/papers/{id}/download — proxy-download a PDF from Drive
  POST /api/papers/{id}/summarize — AI question-by-question summary
  POST /api/admin/refresh-index  — rebuild the Drive file index
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from auth import create_session_token, get_current_user, verify_google_token
from chat import ChatHandler
from drive import drive_index
from grade_boundaries import grade_boundary_db
from login_tracker import login_tracker
from paper_analysis import paper_analysis_db
from models import ChatRequest, ChatResponse, PaperAnalysis, SummarizeResponse, User

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DRIVE_ROOT_FOLDER_ID: str = os.environ["DRIVE_ROOT_FOLDER_ID"]
ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]
# Optional — only needed when using service account auth
SERVICE_ACCOUNT_JSON: str = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "http://localhost:5173")
ALLOWED_DOMAINS: list[str] = [
    d.strip() for d in os.environ.get("ALLOWED_EMAIL_DOMAINS", "").split(",") if d.strip()
]
ADMIN_EMAIL: str = os.environ.get("ADMIN_EMAIL", "")

chat_handler: Optional[ChatHandler] = None

# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    global chat_handler
    sa_info = json.loads(SERVICE_ACCOUNT_JSON) if SERVICE_ACCOUNT_JSON else None
    drive_index.initialize(DRIVE_ROOT_FOLDER_ID, service_account_info=sa_info)
    chat_handler = ChatHandler(ANTHROPIC_API_KEY)
    logger.info("Application ready.")
    yield


app = FastAPI(title="IB Past Papers Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def check_email_allowed(email: str):
    if not ALLOWED_DOMAINS:
        return  # open to all Google accounts
    domain = email.split("@")[-1]
    if domain not in ALLOWED_DOMAINS and email not in ALLOWED_DOMAINS:
        raise HTTPException(status_code=403, detail="Your email is not authorised for this platform.")


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------


@app.post("/api/auth/google")
async def google_auth(body: dict, response: Response, request: Request):
    """Exchange a Google ID token (from the frontend) for a session cookie."""
    token = body.get("credential")
    if not token:
        raise HTTPException(status_code=400, detail="Missing 'credential' field")

    user_info = verify_google_token(token)
    email = user_info.get("email", "")
    check_email_allowed(email)

    user = User(
        email=email,
        name=user_info.get("name", "Student"),
        picture=user_info.get("picture"),
    )
    session_token = create_session_token(user)
    is_production = os.environ.get("ENV") == "production"
    response.set_cookie(
        "session",
        session_token,
        httponly=True,
        samesite="none" if is_production else "lax",
        secure=is_production,
        max_age=30 * 24 * 60 * 60,
    )

    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else None)
    login_tracker.record(email=email, name=user.name, picture=user.picture, ip_address=ip)

    return {"user": user}


@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie("session")
    return {"ok": True}


@app.get("/api/auth/me")
async def me(user: User = Depends(get_current_user)):
    return user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _attach_analysis(groups):
    """Attach stored analysis (topics, difficulty) to each PaperGroup if available."""
    from models import PaperAnalysis
    for group in groups:
        if group.question_paper:
            data = paper_analysis_db.get(group.question_paper.file_id)
            if data:
                group.analysis = PaperAnalysis(
                    difficulty=data.get("difficulty"),
                    topics=data.get("topics", []),
                    section_b_topics=data.get("section_b_topics", []),
                )
    return groups


# ---------------------------------------------------------------------------
# Chat route
# ---------------------------------------------------------------------------


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user: User = Depends(get_current_user)):
    parsed = chat_handler.parse_query(request.message)

    if parsed.resource_type == "data_booklet":
        files = drive_index.search(
            subject=parsed.subject,
            level=None,  # data booklets are shared across HL/SL
            resource_type="data_booklet",
        )
        # Fall back to all data booklets if subject match returns nothing
        if not files:
            files = drive_index.search(resource_type="data_booklet")
        message = chat_handler.build_resource_response(parsed, files)
        return ChatResponse(message=message, resource_files=files)

    if parsed.resource_type == "grade_boundary":
        message = chat_handler.build_grade_boundary_response(parsed)
        return ChatResponse(message=message)

    if parsed.resource_type == "topic_search" and parsed.topic_query:
        file_ids = paper_analysis_db.search(
            topic=parsed.topic_query,
            subject=parsed.subject,
            level=parsed.level,
            section=parsed.section,
        )
        files = [f for f in drive_index.papers if f.file_id in file_ids and f.type == "question"]
        groups = drive_index.group_results(files)
        groups = _attach_analysis(groups)
        message = chat_handler.build_topic_search_response(parsed, groups)
        return ChatResponse(message=message, paper_groups=groups)

    files = drive_index.search(
        subject=parsed.subject,
        level=parsed.level,
        year=parsed.year,
        session=parsed.session,
        paper=parsed.paper,
        timezone=parsed.timezone,
    )
    groups = drive_index.group_results(files)
    groups = _attach_analysis(groups)
    message = chat_handler.build_response_message(parsed, groups)
    return ChatResponse(message=message, paper_groups=groups)


# ---------------------------------------------------------------------------
# Paper routes
# ---------------------------------------------------------------------------


@app.get("/api/papers/{file_id}/download")
async def download_paper(file_id: str, user: User = Depends(get_current_user)):
    try:
        pdf_bytes, filename = drive_index.get_file_bytes(file_id)
    except Exception as e:
        logger.error(f"Download error for {file_id}: {e}")
        raise HTTPException(status_code=404, detail="File not found in Drive")

    # Append year and session to filename if available
    paper = drive_index.get_paper_by_id(file_id)
    if paper:
        suffix_parts = []
        if paper.year:
            suffix_parts.append(str(paper.year))
        if paper.session:
            suffix_parts.append(paper.session)
        if suffix_parts:
            stem, ext = filename.rsplit(".", 1) if "." in filename else (filename, "pdf")
            filename = f"{stem}_{'_'.join(suffix_parts)}.{ext}"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/papers/{file_id}/summarize", response_model=SummarizeResponse)
async def summarize_paper(file_id: str, user: User = Depends(get_current_user)):
    paper = drive_index.get_paper_by_id(file_id)
    if paper and paper.type == "markscheme":
        raise HTTPException(status_code=400, detail="AI Summary is only available for question papers, not markschemes.")
    try:
        text = drive_index.get_text_from_pdf(file_id)
    except Exception as e:
        logger.error(f"Summarize error for {file_id}: {e}")
        raise HTTPException(status_code=404, detail="File not found in Drive")
    summary = chat_handler.summarize_paper(text)
    return SummarizeResponse(summary=summary)


# ---------------------------------------------------------------------------
# Admin route
# ---------------------------------------------------------------------------


@app.get("/api/admin/logins")
async def admin_logins(user: User = Depends(get_current_user)):
    if user.email != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Admin only")
    return {
        "total_logins": login_tracker.total_count(),
        "users": login_tracker.get_unique_users(),
        "recent": login_tracker.get_all(limit=100),
    }


@app.post("/api/admin/refresh-index")
async def refresh_index(user: User = Depends(get_current_user)):
    if user.email != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Admin only")
    drive_index.refresh(DRIVE_ROOT_FOLDER_ID)
    return {"files_indexed": len(drive_index.papers)}


@app.post("/api/admin/analyze-papers")
async def analyze_papers_endpoint(user: User = Depends(get_current_user)):
    if user.email != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Admin only")
    import subprocess, sys
    subprocess.Popen([sys.executable, "analyze_papers.py"])
    return {"status": "Analysis started in background. Check server logs for progress."}


@app.post("/api/admin/scrape-grade-boundaries")
async def scrape_grade_boundaries(user: User = Depends(get_current_user)):
    if user.email != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Admin only")
    total = grade_boundary_db.scrape_all()
    return {"rows_scraped": total, "total_in_db": grade_boundary_db.row_count()}


@app.get("/api/admin/debug-index")
async def debug_index():
    sample = drive_index.papers[:20]
    return {
        "total": len(drive_index.papers),
        "sample": [
            {
                "filename": p.filename,
                "subject": p.subject,
                "level": p.level,
                "year": p.year,
                "session": p.session,
                "paper": p.paper,
                "timezone": p.timezone,
            }
            for p in sample
        ],
    }

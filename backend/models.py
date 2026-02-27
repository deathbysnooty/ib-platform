from pydantic import BaseModel
from typing import Optional, List, Literal


class PaperFile(BaseModel):
    file_id: str
    filename: str
    subject: Optional[str] = None
    level: Optional[str] = None
    year: Optional[int] = None
    session: Optional[str] = None
    paper: Optional[int] = None
    timezone: Optional[str] = None
    type: Literal["question", "markscheme", "data_booklet"] = "question"
    folder_path: str = ""


class PaperAnalysis(BaseModel):
    difficulty: Optional[str] = None
    topics: List[str] = []
    section_b_topics: List[str] = []


class PaperGroup(BaseModel):
    subject: str
    level: Optional[str] = None
    year: Optional[int] = None
    session: Optional[str] = None
    paper: Optional[int] = None
    timezone: str
    question_paper: Optional[PaperFile] = None
    markscheme: Optional[PaperFile] = None
    analysis: Optional[PaperAnalysis] = None


class ParsedQuery(BaseModel):
    subject: Optional[str] = None
    level: Optional[str] = None
    year: Optional[int] = None
    session: Optional[str] = None
    paper: Optional[int] = None
    timezone: Optional[str] = None
    resource_type: Optional[str] = None  # "data_booklet" | "grade_boundary" | "topic_search" | None
    score: Optional[int] = None           # raw mark for grade boundary lookup
    topic_query: Optional[str] = None     # e.g. "complex numbers"
    section: Optional[str] = None         # "A" | "B" | None


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    message: str
    paper_groups: List[PaperGroup] = []
    resource_files: List[PaperFile] = []


class SummarizeResponse(BaseModel):
    summary: str


class User(BaseModel):
    email: str
    name: str
    picture: Optional[str] = None

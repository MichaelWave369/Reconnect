from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------- Core ----------------
class CaseCreate(BaseModel):
    title: str
    subject_name: str
    dob: Optional[str] = None  # YYYY-MM-DD
    aliases: Optional[str] = None  # comma-separated
    last_known_locations: Optional[str] = None  # comma-separated
    relatives: Optional[str] = None  # comma-separated
    notes: Optional[str] = None


class CaseOut(CaseCreate):
    id: str
    created_at: str
    updated_at: str


class EvidenceCreate(BaseModel):
    kind: Literal["note", "link", "file"] = "note"
    title: str
    url: Optional[str] = None
    content: Optional[str] = None
    event_date: Optional[str] = None  # YYYY-MM-DD
    sensitive: bool = False


class EvidenceOut(EvidenceCreate):
    id: str
    case_id: str
    file_path: Optional[str] = None
    created_at: str


class TimelineEventCreate(BaseModel):
    event_type: str = "note"
    title: str
    event_date: Optional[str] = None  # YYYY-MM-DD
    data: Dict[str, Any] = Field(default_factory=dict)


class TimelineEventOut(TimelineEventCreate):
    id: str
    case_id: str
    created_at: str


# compatibility aliases used by main.py
EventCreate = TimelineEventCreate
EventOut = TimelineEventOut


# ---------------- Search ----------------
class SearchQuery(BaseModel):
    full_name: str
    dob: Optional[str] = None
    aliases: Optional[str] = None
    location: Optional[str] = None
    relatives: Optional[str] = None
    notes: Optional[str] = None
    local_only: bool = True


class SourceLink(BaseModel):
    source: str
    url: str
    notes: str = ""
    category: str = "linkout"


class SearchResult(BaseModel):
    status: Literal["linkouts", "cached"]
    cached: bool
    query_hash: str
    results: List[SourceLink]
    created_at: str
    changed_since_last: bool = False


class SearchRunOut(BaseModel):
    id: str
    case_id: str
    query: Dict[str, Any]
    results: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    cached: bool
    created_at: str


# ---------------- Tags ----------------
class TagCreate(BaseModel):
    label: str
    color: Optional[str] = None


class TagOut(BaseModel):
    id: str
    label: str
    color: Optional[str] = None
    created_at: str


# ---------------- Tasks ----------------
class TaskCreate(BaseModel):
    title: str
    due_date: Optional[str] = None  # YYYY-MM-DD
    priority: int = 2
    notes: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None  # open|in_progress|blocked|done
    due_date: Optional[str] = None
    priority: Optional[int] = None
    notes: Optional[str] = None


class TaskOut(BaseModel):
    id: str
    case_id: str
    title: str
    status: str
    due_date: Optional[str] = None
    priority: int
    notes: Optional[str] = None
    created_at: str
    updated_at: str


# ---------------- Documents ----------------
class DocumentRenderRequest(BaseModel):
    doc_type: str
    requester_name: Optional[str] = None
    requester_relation: Optional[str] = None
    requester_phone: Optional[str] = None
    requester_email: Optional[str] = None
    addresses: Optional[str] = None
    last_contact_year: Optional[str] = None
    title: Optional[str] = None


class DocumentOut(BaseModel):
    id: str
    case_id: str
    doc_type: str
    title: str
    content: str
    created_at: str


# ---------------- Audit ----------------
class AuditOut(BaseModel):
    id: str
    actor: str
    action: str
    case_id: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
    created_at: str

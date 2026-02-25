from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db, db_cursor, UPLOAD_DIR, DB_PATH
from .schemas import (
    CaseCreate,
    CaseOut,
    EventCreate,
    EventOut,
    EvidenceCreate,
    EvidenceOut,
    SearchQuery,
    SearchRunOut,
    TagCreate,
    TagOut,
    TaskCreate,
    TaskUpdate,
    TaskOut,
    DocumentRenderRequest,
    DocumentOut,
    AuditOut,
)
from .utils import new_id, now_iso
from .services.search import run_linkout_search
from .services.redact import redact_text
from .services.vector import hash_embed, image_ahash_embed, upsert_vector, query_similar
from .services.export import generate_case_packet
from .services.ollama import summarize_case
from .services.documents import render_document, render_pdf_bytes
from .services.graph import build_case_graph
from .services.global_search import global_search, rebuild_fts
from .services.states import get_state_guidance, get_all_states

# ---------------- App ----------------
app = FastAPI(title="Reconnect", version="1.0.1")


def _cors_origins() -> List[str]:
    """CORS is only needed if you host the UI separately.

    Default is restricted to localhost to reduce accidental exposure.
    You can override via RECONNECT_CORS_ORIGINS (comma-separated).
    """
    raw = os.getenv(
        "RECONNECT_CORS_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000",
    )
    return [o.strip() for o in raw.split(",") if o.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UI_DIR = Path(__file__).parent / "static" / "ui"
app.mount("/static", StaticFiles(directory=str(UI_DIR)), name="static")


@app.on_event("startup")
def _startup():
    init_db()
    # Best-effort: ensure FTS exists and is populated
    try:
        rebuild_fts()
    except Exception:
        pass


def _actor(headers: Dict[str, str]) -> str:
    # Optional header override for audit, if needed later.
    return headers.get("x-actor", "local")


def audit(
    action: str, actor: str, case_id: Optional[str] = None, meta: Optional[Dict[str, Any]] = None
) -> None:
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO audit_log(id, actor, action, case_id, meta_json, created_at) VALUES (?,?,?,?,?,?)",
            (
                new_id("a_"),
                actor,
                action,
                case_id,
                json.dumps(meta or {}, ensure_ascii=False),
                now_iso(),
            ),
        )


# ---------------- UI ----------------
@app.get("/", response_class=HTMLResponse)
def root():
    return HTMLResponse((UI_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/health")
def health():
    return {
        "ok": True,
        "db": str(DB_PATH),
        "uploads": str(UPLOAD_DIR),
        "version": app.version,
    }


# ---------------- State Vital Records ----------------
@app.get("/states/{state_abbrev}")
def get_state_info(state_abbrev: str):
    return get_state_guidance(state_abbrev, "")


@app.get("/states")
def list_states():
    return get_all_states()


# ---------------- Cases ----------------
@app.post("/cases", response_model=CaseOut)
def create_case(payload: CaseCreate, request: Request):
    case_id = new_id("c_")
    now = now_iso()
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO cases(id, title, subject_name, dob, aliases, last_known_locations, relatives, notes, created_at, updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                case_id,
                payload.title,
                payload.subject_name,
                payload.dob,
                payload.aliases,
                payload.last_known_locations,
                payload.relatives,
                payload.notes,
                now,
                now,
            ),
        )
    audit("case.created", _actor(request.headers), case_id, {"title": payload.title})
    try:
        rebuild_fts(case_id)
    except Exception:
        pass
    return get_case(case_id)


@app.get("/cases", response_model=List[CaseOut])
def list_cases():
    with db_cursor() as cur:
        rows = cur.execute("SELECT * FROM cases ORDER BY updated_at DESC").fetchall()
    return [dict(r) for r in rows]


@app.get("/cases/{case_id}", response_model=CaseOut)
def get_case(case_id: str):
    with db_cursor() as cur:
        row = cur.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Case not found")
    return dict(row)


@app.patch("/cases/{case_id}", response_model=CaseOut)
def update_case(case_id: str, payload: CaseCreate, request: Request):
    now = now_iso()
    with db_cursor() as cur:
        cur.execute(
            """
            UPDATE cases
            SET title=?, subject_name=?, dob=?, aliases=?, last_known_locations=?, relatives=?, notes=?, updated_at=?
            WHERE id=?
            """,
            (
                payload.title,
                payload.subject_name,
                payload.dob,
                payload.aliases,
                payload.last_known_locations,
                payload.relatives,
                payload.notes,
                now,
                case_id,
            ),
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "Case not found")
    audit("case.updated", _actor(request.headers), case_id, {"title": payload.title})
    try:
        rebuild_fts(case_id)
    except Exception:
        pass
    return get_case(case_id)


@app.delete("/cases/{case_id}")
def delete_case(case_id: str, request: Request):
    with db_cursor() as cur:
        cur.execute("DELETE FROM cases WHERE id=?", (case_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Case not found")
    audit("case.deleted", _actor(request.headers), case_id)
    return {"ok": True}


# ---------------- Tags ----------------
@app.get("/tags", response_model=List[TagOut])
def list_tags():
    with db_cursor() as cur:
        rows = cur.execute("SELECT * FROM tags ORDER BY label ASC").fetchall()
    return [dict(r) for r in rows]


@app.post("/tags", response_model=TagOut)
def create_tag(payload: TagCreate, request: Request):
    tag_id = new_id("t_")
    now = now_iso()
    label = payload.label.strip()
    if not label:
        raise HTTPException(400, "label required")
    with db_cursor() as cur:
        try:
            cur.execute(
                "INSERT INTO tags(id, label, color, created_at) VALUES (?,?,?,?)",
                (tag_id, label, payload.color, now),
            )
        except Exception:
            raise HTTPException(409, "Tag label already exists")
    audit("tag.created", _actor(request.headers), None, {"label": label})
    return {"id": tag_id, "label": label, "color": payload.color, "created_at": now}


@app.delete("/tags/{tag_id}")
def delete_tag(tag_id: str, request: Request):
    with db_cursor() as cur:
        cur.execute("DELETE FROM tags WHERE id=?", (tag_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Tag not found")
    audit("tag.deleted", _actor(request.headers), None, {"tag_id": tag_id})
    return {"ok": True}


@app.get("/cases/{case_id}/tags", response_model=List[TagOut])
def list_case_tags(case_id: str):
    with db_cursor() as cur:
        rows = cur.execute(
            """
            SELECT t.* FROM tags t
            JOIN case_tags ct ON ct.tag_id=t.id
            WHERE ct.case_id=?
            ORDER BY t.label ASC
            """,
            (case_id,),
        ).fetchall()
    return [dict(r) for r in rows]


@app.post("/cases/{case_id}/tags/{tag_id}")
def add_case_tag(case_id: str, tag_id: str, request: Request):
    now = now_iso()
    with db_cursor() as cur:
        cur.execute("SELECT id FROM cases WHERE id=?", (case_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Case not found")
        cur.execute("SELECT id FROM tags WHERE id=?", (tag_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Tag not found")
        cur.execute(
            "INSERT OR IGNORE INTO case_tags(case_id, tag_id, created_at) VALUES (?,?,?)",
            (case_id, tag_id, now),
        )
    audit("case.tag.added", _actor(request.headers), case_id, {"tag_id": tag_id})
    return {"ok": True}


@app.delete("/cases/{case_id}/tags/{tag_id}")
def remove_case_tag(case_id: str, tag_id: str, request: Request):
    with db_cursor() as cur:
        cur.execute("DELETE FROM case_tags WHERE case_id=? AND tag_id=?", (case_id, tag_id))
    audit("case.tag.removed", _actor(request.headers), case_id, {"tag_id": tag_id})
    return {"ok": True}


# ---------------- Tasks ----------------
@app.get("/cases/{case_id}/tasks", response_model=List[TaskOut])
def list_tasks(case_id: str, status: Optional[str] = None):
    with db_cursor() as cur:
        if status:
            rows = cur.execute(
                "SELECT * FROM tasks WHERE case_id=? AND status=? ORDER BY COALESCE(due_date,'9999-99-99') ASC, priority ASC, created_at ASC",
                (case_id, status),
            ).fetchall()
        else:
            rows = cur.execute(
                "SELECT * FROM tasks WHERE case_id=? ORDER BY CASE status WHEN 'open' THEN 1 WHEN 'in_progress' THEN 2 WHEN 'blocked' THEN 3 WHEN 'done' THEN 4 ELSE 5 END, COALESCE(due_date,'9999-99-99') ASC, priority ASC, created_at ASC",
                (case_id,),
            ).fetchall()
    return [dict(r) for r in rows]


@app.post("/cases/{case_id}/tasks", response_model=TaskOut)
def create_task(case_id: str, payload: TaskCreate, request: Request):
    task_id = new_id("k_")
    now = now_iso()
    with db_cursor() as cur:
        cur.execute("SELECT id FROM cases WHERE id=?", (case_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Case not found")
        cur.execute(
            "INSERT INTO tasks(id, case_id, title, status, due_date, priority, notes, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                task_id,
                case_id,
                payload.title.strip(),
                "open",
                payload.due_date,
                int(payload.priority),
                payload.notes,
                now,
                now,
            ),
        )
    # index task for search and retrieval
    upsert_vector(
        case_id=case_id,
        ref_type="task",
        ref_id=task_id,
        modality="text",
        vec=hash_embed((payload.title or "") + "\n" + (payload.notes or "")),
        meta={"title": payload.title},
    )
    audit(
        "task.created",
        _actor(request.headers),
        case_id,
        {"task_id": task_id, "title": payload.title},
    )
    try:
        rebuild_fts(case_id)
    except Exception:
        pass
    return {
        "id": task_id,
        "case_id": case_id,
        "title": payload.title.strip(),
        "status": "open",
        "due_date": payload.due_date,
        "priority": int(payload.priority),
        "notes": payload.notes,
        "created_at": now,
        "updated_at": now,
    }


@app.patch("/cases/{case_id}/tasks/{task_id}", response_model=TaskOut)
def update_task(case_id: str, task_id: str, payload: TaskUpdate, request: Request):
    with db_cursor() as cur:
        row = cur.execute(
            "SELECT * FROM tasks WHERE id=? AND case_id=?", (task_id, case_id)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Task not found")
        new_title = payload.title if payload.title is not None else row["title"]
        new_status = payload.status if payload.status is not None else row["status"]
        new_due = payload.due_date if payload.due_date is not None else row["due_date"]
        new_pri = int(payload.priority) if payload.priority is not None else int(row["priority"])
        new_notes = payload.notes if payload.notes is not None else row["notes"]
        now = now_iso()
        cur.execute(
            "UPDATE tasks SET title=?, status=?, due_date=?, priority=?, notes=?, updated_at=? WHERE id=? AND case_id=?",
            (new_title, new_status, new_due, new_pri, new_notes, now, task_id, case_id),
        )
    upsert_vector(
        case_id=case_id,
        ref_type="task",
        ref_id=task_id,
        modality="text",
        vec=hash_embed((new_title or "") + "\n" + (new_notes or "")),
        meta={"title": new_title},
    )
    audit("task.updated", _actor(request.headers), case_id, {"task_id": task_id})
    try:
        rebuild_fts(case_id)
    except Exception:
        pass
    return {
        "id": task_id,
        "case_id": case_id,
        "title": new_title,
        "status": new_status,
        "due_date": new_due,
        "priority": new_pri,
        "notes": new_notes,
        "created_at": row["created_at"],
        "updated_at": now,
    }


@app.delete("/cases/{case_id}/tasks/{task_id}")
def delete_task(case_id: str, task_id: str, request: Request):
    with db_cursor() as cur:
        cur.execute("DELETE FROM tasks WHERE id=? AND case_id=?", (task_id, case_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Task not found")
    audit("task.deleted", _actor(request.headers), case_id, {"task_id": task_id})
    try:
        rebuild_fts(case_id)
    except Exception:
        pass
    return {"ok": True}


# ---------------- Timeline ----------------
@app.get("/cases/{case_id}/timeline", response_model=List[EventOut])
def list_events(case_id: str):
    with db_cursor() as cur:
        rows = cur.execute(
            "SELECT * FROM events WHERE case_id=? ORDER BY COALESCE(event_date,'9999-99-99') ASC, created_at ASC",
            (case_id,),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["data"] = json.loads(d.get("data_json") or "{}")
        except Exception:
            d["data"] = {}
        d.pop("data_json", None)
        out.append(d)
    return out


@app.post("/cases/{case_id}/timeline", response_model=EventOut)
def add_event(case_id: str, payload: EventCreate, request: Request):
    ev_id = new_id("e_")
    now = now_iso()
    with db_cursor() as cur:
        cur.execute("SELECT id FROM cases WHERE id=?", (case_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Case not found")
        cur.execute(
            "INSERT INTO events(id, case_id, event_type, title, event_date, data_json, created_at) VALUES (?,?,?,?,?,?,?)",
            (
                ev_id,
                case_id,
                payload.event_type,
                payload.title,
                payload.event_date,
                json.dumps(payload.data or {}, ensure_ascii=False),
                now,
            ),
        )
    audit(
        "timeline.event.added",
        _actor(request.headers),
        case_id,
        {"event_id": ev_id, "title": payload.title},
    )
    return {
        "id": ev_id,
        "case_id": case_id,
        "event_type": payload.event_type,
        "title": payload.title,
        "event_date": payload.event_date,
        "data": payload.data or {},
        "created_at": now,
    }


@app.delete("/cases/{case_id}/timeline/{event_id}")
def delete_event(case_id: str, event_id: str, request: Request):
    with db_cursor() as cur:
        cur.execute("DELETE FROM events WHERE id=? AND case_id=?", (event_id, case_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Event not found")
    audit("timeline.event.deleted", _actor(request.headers), case_id, {"event_id": event_id})
    return {"ok": True}


# ---------------- Evidence ----------------
@app.get("/cases/{case_id}/evidence", response_model=List[EvidenceOut])
def list_evidence(case_id: str):
    with db_cursor() as cur:
        rows = cur.execute(
            "SELECT * FROM evidence_items WHERE case_id=? ORDER BY COALESCE(event_date,'9999-99-99') ASC, created_at ASC",
            (case_id,),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["sensitive"] = bool(d.get("sensitive", 0))
        # Always return redacted content (more aggressive if flagged sensitive)
        if d.get("content"):
            d["content"] = redact_text(d["content"], sensitive=d["sensitive"])
        out.append(d)
    return out


@app.post("/cases/{case_id}/evidence", response_model=EvidenceOut)
def add_evidence(case_id: str, payload: EvidenceCreate, request: Request):
    ev_id = new_id("v_")
    now = now_iso()
    with db_cursor() as cur:
        cur.execute("SELECT id FROM cases WHERE id=?", (case_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Case not found")
        cur.execute(
            """
            INSERT INTO evidence_items(id, case_id, kind, title, url, content, file_path, event_date, sensitive, created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                ev_id,
                case_id,
                payload.kind,
                payload.title,
                payload.url,
                payload.content,
                None,
                payload.event_date,
                1 if payload.sensitive else 0,
                now,
            ),
        )

    # Index for similarity and retrieval (text only)
    blob = (payload.title or "") + "\n" + (payload.url or "") + "\n" + (payload.content or "")
    upsert_vector(
        case_id=case_id,
        ref_type="evidence",
        ref_id=ev_id,
        modality="text",
        vec=hash_embed(blob),
        meta={"title": payload.title, "kind": payload.kind},
    )

    audit(
        "evidence.added",
        _actor(request.headers),
        case_id,
        {"evidence_id": ev_id, "kind": payload.kind},
    )
    try:
        rebuild_fts(case_id)
    except Exception:
        pass
    return {
        "id": ev_id,
        "case_id": case_id,
        **payload.model_dump(),
        "file_path": None,
        "created_at": now,
    }


@app.post("/cases/{case_id}/evidence/upload", response_model=EvidenceOut)
async def upload_evidence_file(
    case_id: str,
    request: Request,
    file: UploadFile = File(...),
    title: str = Form("Uploaded File"),
    event_date: Optional[str] = Form(None),
    sensitive: bool = Form(False),
):
    ev_id = new_id("v_")
    now = now_iso()
    ext = Path(file.filename or "").suffix.lower()
    safe_name = f"{ev_id}{ext}"
    out_path = UPLOAD_DIR / safe_name
    data = await file.read()
    out_path.write_bytes(data)

    with db_cursor() as cur:
        cur.execute("SELECT id FROM cases WHERE id=?", (case_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Case not found")
        cur.execute(
            """
            INSERT INTO evidence_items(id, case_id, kind, title, url, content, file_path, event_date, sensitive, created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                ev_id,
                case_id,
                "file",
                title,
                None,
                None,
                str(out_path),
                event_date,
                1 if sensitive else 0,
                now,
            ),
        )

    # If image, compute image hash embedding for similarity
    if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"]:
        vec, meta = image_ahash_embed(data)
        upsert_vector(
            case_id=case_id, ref_type="evidence", ref_id=ev_id, modality="image", vec=vec, meta=meta
        )

    audit(
        "evidence.uploaded",
        _actor(request.headers),
        case_id,
        {"evidence_id": ev_id, "filename": file.filename},
    )
    try:
        rebuild_fts(case_id)
    except Exception:
        pass
    return {
        "id": ev_id,
        "case_id": case_id,
        "kind": "file",
        "title": title,
        "url": None,
        "content": None,
        "file_path": str(out_path),
        "event_date": event_date,
        "sensitive": sensitive,
        "created_at": now,
    }


@app.get("/evidence/file")
def download_evidence_file(
    path: str = Query(..., description="Absolute path returned by evidence.file_path"),
):
    # Restrict to UPLOAD_DIR
    p = Path(path).resolve()
    if UPLOAD_DIR not in p.parents and p != UPLOAD_DIR:
        raise HTTPException(403, "Forbidden")
    if not p.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(str(p))


@app.delete("/cases/{case_id}/evidence/{evidence_id}")
def delete_evidence(case_id: str, evidence_id: str, request: Request):
    with db_cursor() as cur:
        row = cur.execute(
            "SELECT file_path FROM evidence_items WHERE id=? AND case_id=?", (evidence_id, case_id)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Evidence not found")
        cur.execute("DELETE FROM evidence_items WHERE id=? AND case_id=?", (evidence_id, case_id))
    # delete file if exists
    fp = row["file_path"]
    if fp:
        try:
            Path(fp).unlink(missing_ok=True)
        except Exception:
            pass
    audit("evidence.deleted", _actor(request.headers), case_id, {"evidence_id": evidence_id})
    try:
        rebuild_fts(case_id)
    except Exception:
        pass
    return {"ok": True}


# ---------------- Search (linkouts + caching) ----------------
@app.post("/cases/{case_id}/search", response_model=SearchRunOut)
def run_search(case_id: str, payload: SearchQuery, request: Request):
    q = payload.model_dump()
    # local_only just toggles whether we do linkouts; we don't scrape either way.
    result = run_linkout_search(q)

    run_id = new_id("s_")
    now = now_iso()
    with db_cursor() as cur:
        cur.execute("SELECT id FROM cases WHERE id=?", (case_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Case not found")
        cur.execute(
            """
            INSERT INTO search_runs(id, case_id, query_json, results_json, sources_json, cached, created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                run_id,
                case_id,
                json.dumps(q, ensure_ascii=False),
                json.dumps(result["results"], ensure_ascii=False),
                json.dumps(
                    [
                        {"source": r["source"], "category": r.get("category")}
                        for r in result["results"]
                    ],
                    ensure_ascii=False,
                ),
                1 if result.get("cached") else 0,
                now,
            ),
        )

    # Index search run
    text_blob = (
        json.dumps(q, ensure_ascii=False)
        + "\n"
        + " ".join([r.get("source", "") + " " + r.get("url", "") for r in result["results"]])
    )
    upsert_vector(
        case_id=case_id,
        ref_type="search_run",
        ref_id=run_id,
        modality="text",
        vec=hash_embed(text_blob),
        meta={"query_hash": result.get("query_hash")},
    )

    audit(
        "search.run",
        _actor(request.headers),
        case_id,
        {"search_run_id": run_id, "cached": result.get("cached", False)},
    )
    return {
        "id": run_id,
        "case_id": case_id,
        "query": q,
        "results": result["results"],
        "sources": [
            {"source": r["source"], "category": r.get("category"), "url": r["url"]}
            for r in result["results"]
        ],
        "cached": bool(result.get("cached")),
        "created_at": now,
    }


@app.get("/cases/{case_id}/search-runs", response_model=List[SearchRunOut])
def list_search_runs(case_id: str):
    with db_cursor() as cur:
        rows = cur.execute(
            "SELECT * FROM search_runs WHERE case_id=? ORDER BY created_at DESC", (case_id,)
        ).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "case_id": r["case_id"],
                "query": json.loads(r["query_json"]),
                "results": json.loads(r["results_json"]),
                "sources": json.loads(r["sources_json"]),
                "cached": bool(r["cached"]),
                "created_at": r["created_at"],
            }
        )
    return out


# ---------------- Similarity ----------------
@app.get("/cases/{case_id}/similarity")
def similarity(
    case_id: str,
    q: str = Query(..., description="Text query or file path for images"),
    modality: str = Query("text", pattern="^(text|image)$"),
    top_k: int = Query(8, ge=1, le=25),
):
    if modality == "text":
        vec = hash_embed(q)
    else:
        # q is a file_path pointing to UPLOAD_DIR
        p = Path(q).resolve()
        if UPLOAD_DIR not in p.parents and p != UPLOAD_DIR:
            raise HTTPException(403, "Forbidden")
        if not p.exists():
            raise HTTPException(404, "File not found")
        vec, _meta = image_ahash_embed(p.read_bytes())

    hits = query_similar(case_id=case_id, modality=modality, vec=vec, top_k=top_k)

    # Return resolved references
    resolved = []
    with db_cursor() as cur:
        for vid, score, ref_type, ref_id, meta in hits:
            title = None
            if ref_type == "evidence":
                row = cur.execute(
                    "SELECT title, kind FROM evidence_items WHERE id=?", (ref_id,)
                ).fetchone()
                if row:
                    title = row["title"]
            elif ref_type == "search_run":
                title = "Search run"
            elif ref_type == "task":
                row = cur.execute("SELECT title FROM tasks WHERE id=?", (ref_id,)).fetchone()
                if row:
                    title = row["title"]
            elif ref_type == "doc":
                row = cur.execute("SELECT title FROM documents WHERE id=?", (ref_id,)).fetchone()
                if row:
                    title = row["title"]

            resolved.append(
                {
                    "vector_id": vid,
                    "score": round(float(score), 6),
                    "ref_type": ref_type,
                    "ref_id": ref_id,
                    "title": title,
                    "meta": meta,
                }
            )
    return {"case_id": case_id, "modality": modality, "hits": resolved}


# ---------------- Documents ----------------
@app.get("/cases/{case_id}/documents", response_model=List[DocumentOut])
def list_documents(case_id: str):
    with db_cursor() as cur:
        rows = cur.execute(
            "SELECT * FROM documents WHERE case_id=? ORDER BY created_at DESC", (case_id,)
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/cases/{case_id}/documents/{doc_id}", response_model=DocumentOut)
def get_document(case_id: str, doc_id: str):
    with db_cursor() as cur:
        row = cur.execute(
            "SELECT * FROM documents WHERE id=? AND case_id=?", (doc_id, case_id)
        ).fetchone()
    if not row:
        raise HTTPException(404, "Document not found")
    return dict(row)


@app.get("/cases/{case_id}/documents/{doc_id}.pdf")
def get_document_pdf(case_id: str, doc_id: str):
    doc = get_document(case_id, doc_id)
    pdf = render_pdf_bytes(doc["title"], doc["content"])
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={doc_id}.pdf"},
    )


@app.post("/cases/{case_id}/documents/render", response_model=DocumentOut)
def render_and_store_document(case_id: str, payload: DocumentRenderRequest, request: Request):
    case = get_case(case_id)
    ctx = {
        "case_id": case_id,
        "case_title": case["title"],
        "subject_name": case["subject_name"],
        "dob": case.get("dob") or "",
        "last_known_locations": case.get("last_known_locations") or "",
        "requester_name": payload.requester_name or "",
        "requester_relation": payload.requester_relation or "",
        "requester_phone": payload.requester_phone or "",
        "requester_email": payload.requester_email or "",
        "addresses": payload.addresses or "",
        "last_contact_year": payload.last_contact_year or "",
    }
    rendered = render_document(payload.doc_type, ctx)
    doc_id = new_id("d_")
    now = now_iso()
    title = payload.title.strip() if payload.title else rendered.title
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO documents(id, case_id, doc_type, title, content, created_at) VALUES (?,?,?,?,?,?)",
            (doc_id, case_id, payload.doc_type, title, rendered.content, now),
        )
    # Index for retrieval
    upsert_vector(
        case_id=case_id,
        ref_type="doc",
        ref_id=doc_id,
        modality="text",
        vec=hash_embed(title + "\n" + rendered.content),
        meta={"doc_type": payload.doc_type},
    )
    audit(
        "document.rendered",
        _actor(request.headers),
        case_id,
        {"doc_id": doc_id, "doc_type": payload.doc_type},
    )
    try:
        rebuild_fts(case_id)
    except Exception:
        pass
    return {
        "id": doc_id,
        "case_id": case_id,
        "doc_type": payload.doc_type,
        "title": title,
        "content": rendered.content,
        "created_at": now,
    }


@app.delete("/cases/{case_id}/documents/{doc_id}")
def delete_document(case_id: str, doc_id: str, request: Request):
    with db_cursor() as cur:
        cur.execute("DELETE FROM documents WHERE id=? AND case_id=?", (doc_id, case_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Document not found")
    audit("document.deleted", _actor(request.headers), case_id, {"doc_id": doc_id})
    try:
        rebuild_fts(case_id)
    except Exception:
        pass
    return {"ok": True}


# ---------------- Graph ----------------


@app.get("/cases/{case_id}/citations")
def citation_map(case_id: str):
    """
    Returns a stable-ish, human-friendly mapping like E1..En -> evidence items.
    Useful for referencing evidence in notes and generated docs.
    """
    with db_cursor() as cur:
        rows = cur.execute(
            "SELECT id, kind, title, url, event_date, created_at FROM evidence_items WHERE case_id=? "
            "ORDER BY COALESCE(event_date,'9999-99-99') ASC, created_at ASC",
            (case_id,),
        ).fetchall()
    out = []
    for i, r in enumerate(rows, start=1):
        d = dict(r)
        out.append(
            {
                "key": f"E{i}",
                "evidence_id": d["id"],
                "kind": d["kind"],
                "title": d["title"],
                "url": d.get("url"),
                "event_date": d.get("event_date"),
                "created_at": d.get("created_at"),
            }
        )
    return {"case_id": case_id, "map": out}


@app.get("/cases/{case_id}/graph")
def case_graph(case_id: str):
    with db_cursor() as cur:
        case = cur.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if not case:
            raise HTTPException(404, "Case not found")
        ev = cur.execute("SELECT * FROM evidence_items WHERE case_id=?", (case_id,)).fetchall()
    return build_case_graph(dict(case), [dict(r) for r in ev])


# ---------------- Global Search ----------------
@app.get("/search")
def search(
    q: str = Query(...), case_id: Optional[str] = Query(None), limit: int = Query(30, ge=1, le=200)
):
    results = global_search(q, case_id=case_id, limit=limit)
    return {"q": q, "case_id": case_id, "results": results}


# ---------------- RAG summary ----------------
@app.post("/cases/{case_id}/rag/summary")
def rag_summary(case_id: str, request: Request):
    case = get_case(case_id)
    with db_cursor() as cur:
        ev = cur.execute(
            "SELECT title, url, content FROM evidence_items WHERE case_id=? ORDER BY created_at DESC LIMIT 20",
            (case_id,),
        ).fetchall()
    evidence_blob = "\n\n".join(
        [f"- {r['title']}\n{r['url'] or ''}\n{(r['content'] or '')[:1200]}" for r in ev]
    )
    evidence_blob = redact_text(evidence_blob, sensitive=True)
    summary = summarize_case({"case": case, "evidence": evidence_blob})
    audit("rag.summary", _actor(request.headers), case_id, {})
    return summary


@app.get("/cases/{case_id}/rag/retrieve")
def rag_retrieve(case_id: str, q: str = Query(...), top_k: int = Query(6, ge=1, le=25)):
    vec = hash_embed(q)
    hits = query_similar(case_id=case_id, modality="text", vec=vec, top_k=top_k)
    # resolve evidence/doc/task titles and snippets
    out = []
    with db_cursor() as cur:
        for vid, score, ref_type, ref_id, meta in hits:
            title = None
            snippet = ""
            if ref_type == "evidence":
                r = cur.execute(
                    "SELECT title, url, content FROM evidence_items WHERE id=?", (ref_id,)
                ).fetchone()
                if r:
                    title = r["title"]
                    snippet = (r["url"] or "") + "\n" + (r["content"] or "")
            elif ref_type == "task":
                r = cur.execute("SELECT title, notes FROM tasks WHERE id=?", (ref_id,)).fetchone()
                if r:
                    title = r["title"]
                    snippet = r["notes"] or ""
            elif ref_type == "doc":
                r = cur.execute(
                    "SELECT title, content FROM documents WHERE id=?", (ref_id,)
                ).fetchone()
                if r:
                    title = r["title"]
                    snippet = r["content"] or ""
            elif ref_type == "search_run":
                r = cur.execute(
                    "SELECT results_json FROM search_runs WHERE id=?", (ref_id,)
                ).fetchone()
                if r:
                    title = "Search run"
                    snippet = r["results_json"][:800]
            snippet = redact_text(snippet, sensitive=True)[:600]
            out.append(
                {
                    "score": round(float(score), 6),
                    "ref_type": ref_type,
                    "ref_id": ref_id,
                    "title": title,
                    "snippet": snippet,
                }
            )
    return {"q": q, "hits": out}


# ---------------- Export ----------------
@app.get("/cases/{case_id}/export")
def export_case(case_id: str):
    pdf_path = generate_case_packet(case_id)
    return FileResponse(str(pdf_path), media_type="application/pdf", filename=pdf_path.name)


# ---------------- Audit ----------------
@app.get("/audit", response_model=List[AuditOut])
def list_audit(case_id: Optional[str] = None, limit: int = Query(200, ge=1, le=500)):
    with db_cursor() as cur:
        if case_id:
            rows = cur.execute(
                "SELECT * FROM audit_log WHERE case_id=? ORDER BY created_at DESC LIMIT ?",
                (case_id, limit),
            ).fetchall()
        else:
            rows = cur.execute(
                "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
    out = []
    for r in rows:
        meta = {}
        try:
            meta = json.loads(r["meta_json"] or "{}")
        except Exception:
            meta = {}
        out.append(
            {
                "id": r["id"],
                "actor": r["actor"],
                "action": r["action"],
                "case_id": r["case_id"],
                "meta": meta,
                "created_at": r["created_at"],
            }
        )
    return out

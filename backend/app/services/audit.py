from __future__ import annotations

import json
from typing import Any, Dict, Optional

from ..db import db_cursor
from ..utils import new_id, now_iso


def log_action(action: str, actor: str = "local", case_id: Optional[str] = None, meta: Optional[Dict[str, Any]] = None) -> None:
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO audit_log(id, actor, action, case_id, meta_json, created_at) VALUES (?,?,?,?,?,?)",
            (new_id("a_"), actor, action, case_id, json.dumps(meta or {}, ensure_ascii=False), now_iso()),
        )


def list_audit(case_id: Optional[str] = None, limit: int = 200):
    with db_cursor() as cur:
        if case_id:
            rows = cur.execute(
                "SELECT * FROM audit_log WHERE case_id=? ORDER BY created_at DESC LIMIT ?",
                (case_id, limit),
            ).fetchall()
        else:
            rows = cur.execute(
                "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    out = []
    for r in rows:
        meta = {}
        try:
            meta = json.loads(r["meta_json"] or "{}")
        except Exception:
            meta = {}
        out.append({
            "id": r["id"],
            "actor": r["actor"],
            "action": r["action"],
            "case_id": r["case_id"],
            "meta": meta,
            "created_at": r["created_at"],
        })
    return out

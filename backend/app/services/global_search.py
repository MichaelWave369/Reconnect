from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional

from ..db import db_cursor


def _fts_available(cur) -> bool:
    try:
        row = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='fts_all'"
        ).fetchone()
        return row is not None
    except sqlite3.OperationalError:
        return False


def rebuild_fts(case_id: Optional[str] = None) -> None:
    """Rebuild FTS rows from current DB (best effort)."""
    with db_cursor() as cur:
        if not _fts_available(cur):
            return
        if case_id:
            cur.execute("DELETE FROM fts_all WHERE case_id=?", (case_id,))
        else:
            cur.execute("DELETE FROM fts_all")

        # cases
        q_cases = "SELECT id, title, notes, subject_name, aliases, last_known_locations, relatives FROM cases"
        params = ()
        if case_id:
            q_cases += " WHERE id=?"
            params = (case_id,)
        for r in cur.execute(q_cases, params).fetchall():
            body = " ".join(
                [
                    r["subject_name"] or "",
                    r["aliases"] or "",
                    r["last_known_locations"] or "",
                    r["relatives"] or "",
                    r["notes"] or "",
                ]
            )
            cur.execute(
                "INSERT INTO fts_all(case_id, ref_type, ref_id, title, body) VALUES (?,?,?,?,?)",
                (r["id"], "case", r["id"], r["title"], body),
            )

        # evidence
        q_ev = "SELECT id, case_id, title, url, content FROM evidence_items"
        params = ()
        if case_id:
            q_ev += " WHERE case_id=?"
            params = (case_id,)
        for r in cur.execute(q_ev, params).fetchall():
            body = " ".join([r["url"] or "", r["content"] or ""])
            cur.execute(
                "INSERT INTO fts_all(case_id, ref_type, ref_id, title, body) VALUES (?,?,?,?,?)",
                (r["case_id"], "evidence", r["id"], r["title"], body),
            )

        # tasks
        q_t = "SELECT id, case_id, title, notes FROM tasks"
        params = ()
        if case_id:
            q_t += " WHERE case_id=?"
            params = (case_id,)
        for r in cur.execute(q_t, params).fetchall():
            cur.execute(
                "INSERT INTO fts_all(case_id, ref_type, ref_id, title, body) VALUES (?,?,?,?,?)",
                (r["case_id"], "task", r["id"], r["title"], r["notes"] or ""),
            )

        # documents
        q_d = "SELECT id, case_id, title, content FROM documents"
        params = ()
        if case_id:
            q_d += " WHERE case_id=?"
            params = (case_id,)
        for r in cur.execute(q_d, params).fetchall():
            cur.execute(
                "INSERT INTO fts_all(case_id, ref_type, ref_id, title, body) VALUES (?,?,?,?,?)",
                (r["case_id"], "doc", r["id"], r["title"], r["content"] or ""),
            )


def global_search(q: str, case_id: Optional[str] = None, limit: int = 30) -> List[Dict[str, Any]]:
    q = (q or "").strip()
    if not q:
        return []
    with db_cursor() as cur:
        use_fts = _fts_available(cur)
        if use_fts:
            # FTS query; use bm25 for ranking
            where = "fts_all MATCH ?"
            params = [q]
            if case_id:
                where += " AND case_id=?"
                params.append(case_id)
            rows = cur.execute(
                f"""
                SELECT case_id, ref_type, ref_id, title, snippet(fts_all, 4, '[', ']', '…', 12) AS snippet,
                       bm25(fts_all) AS rank
                FROM fts_all
                WHERE {where}
                ORDER BY rank ASC
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()
            return [
                {
                    "case_id": r["case_id"],
                    "ref_type": r["ref_type"],
                    "ref_id": r["ref_id"],
                    "title": r["title"],
                    "snippet": r["snippet"],
                }
                for r in rows
            ]

        # Fallback: LIKE
        like = f"%{q}%"
        out: List[Dict[str, Any]] = []

        def add(rows, ref_type: str, title_key="title", body_key="body"):
            for r in rows:
                out.append(
                    {
                        "case_id": r["case_id"],
                        "ref_type": ref_type,
                        "ref_id": r["id"],
                        "title": r.get(title_key) if isinstance(r, dict) else r[title_key],
                        "snippet": (r.get(body_key) if isinstance(r, dict) else r[body_key])[:160]
                        if (r.get(body_key) if isinstance(r, dict) else r[body_key])
                        else "",
                    }
                )

        if case_id:
            case_rows = cur.execute(
                "SELECT id, id as case_id, title, notes as body FROM cases WHERE id=? AND (title LIKE ? OR notes LIKE ? OR subject_name LIKE ? OR aliases LIKE ? OR last_known_locations LIKE ? OR relatives LIKE ?)",
                (case_id, like, like, like, like, like, like),
            ).fetchall()
        else:
            case_rows = cur.execute(
                "SELECT id, id as case_id, title, notes as body FROM cases WHERE title LIKE ? OR notes LIKE ? OR subject_name LIKE ? OR aliases LIKE ? OR last_known_locations LIKE ? OR relatives LIKE ?",
                (like, like, like, like, like, like),
            ).fetchall()
        out.extend(
            [
                {
                    "case_id": r["case_id"],
                    "ref_type": "case",
                    "ref_id": r["id"],
                    "title": r["title"],
                    "snippet": (r["body"] or "")[:160],
                }
                for r in case_rows
            ]
        )

        if case_id:
            ev_rows = cur.execute(
                "SELECT id, case_id, title, COALESCE(url,'') || ' ' || COALESCE(content,'') as body FROM evidence_items WHERE case_id=? AND (title LIKE ? OR url LIKE ? OR content LIKE ?)",
                (case_id, like, like, like),
            ).fetchall()
        else:
            ev_rows = cur.execute(
                "SELECT id, case_id, title, COALESCE(url,'') || ' ' || COALESCE(content,'') as body FROM evidence_items WHERE title LIKE ? OR url LIKE ? OR content LIKE ?",
                (like, like, like),
            ).fetchall()
        out.extend(
            [
                {
                    "case_id": r["case_id"],
                    "ref_type": "evidence",
                    "ref_id": r["id"],
                    "title": r["title"],
                    "snippet": (r["body"] or "")[:160],
                }
                for r in ev_rows
            ]
        )

        if case_id:
            t_rows = cur.execute(
                "SELECT id, case_id, title, COALESCE(notes,'') as body FROM tasks WHERE case_id=? AND (title LIKE ? OR notes LIKE ?)",
                (case_id, like, like),
            ).fetchall()
        else:
            t_rows = cur.execute(
                "SELECT id, case_id, title, COALESCE(notes,'') as body FROM tasks WHERE title LIKE ? OR notes LIKE ?",
                (like, like),
            ).fetchall()
        out.extend(
            [
                {
                    "case_id": r["case_id"],
                    "ref_type": "task",
                    "ref_id": r["id"],
                    "title": r["title"],
                    "snippet": (r["body"] or "")[:160],
                }
                for r in t_rows
            ]
        )

        if case_id:
            d_rows = cur.execute(
                "SELECT id, case_id, title, SUBSTR(content,1,220) as body FROM documents WHERE case_id=? AND (title LIKE ? OR content LIKE ?)",
                (case_id, like, like),
            ).fetchall()
        else:
            d_rows = cur.execute(
                "SELECT id, case_id, title, SUBSTR(content,1,220) as body FROM documents WHERE title LIKE ? OR content LIKE ?",
                (like, like),
            ).fetchall()
        out.extend(
            [
                {
                    "case_id": r["case_id"],
                    "ref_type": "doc",
                    "ref_id": r["id"],
                    "title": r["title"],
                    "snippet": (r["body"] or "")[:160],
                }
                for r in d_rows
            ]
        )

        return out[:limit]

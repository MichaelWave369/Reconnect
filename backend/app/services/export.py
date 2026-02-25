from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from ..db import UPLOAD_DIR, db_cursor


def _now_utc() -> str:
    return datetime.utcnow().replace(microsecond=0).strftime("%Y-%m-%d %H:%M UTC")


def _wrap_text(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    leading: float = 14,
    font="Helvetica",
    size=10,
) -> float:
    """Draw text with simple wrapping; returns new y."""
    if not text:
        return y
    c.setFont(font, size)
    words = text.split()
    line = ""
    for w in words:
        test = (line + " " + w).strip()
        if c.stringWidth(test, font, size) <= width:
            line = test
        else:
            c.drawString(x, y, line)
            y -= leading
            line = w
            if y < 1.0 * inch:
                c.showPage()
                y = LETTER[1] - 0.75 * inch
                c.setFont(font, size)
    if line:
        c.drawString(x, y, line)
        y -= leading
    return y


def _section_title(c: canvas.Canvas, title: str, x: float, y: float) -> float:
    c.setFont("Helvetica-Bold", 13)
    c.drawString(x, y, title)
    return y - 16


def generate_case_packet(case_id: str) -> Path:
    """Create a PDF case packet with evidence, timeline, tasks, tags, docs, and search runs."""
    out_dir = UPLOAD_DIR / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = (
        out_dir / f"reconnect_case_{case_id}_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.pdf"
    )

    with db_cursor() as cur:
        case_row = cur.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if not case_row:
            raise ValueError("Case not found")

        events = cur.execute(
            "SELECT * FROM events WHERE case_id=? ORDER BY COALESCE(event_date,'9999-99-99') ASC, created_at ASC",
            (case_id,),
        ).fetchall()

        evidence = cur.execute(
            "SELECT * FROM evidence_items WHERE case_id=? ORDER BY COALESCE(event_date,'9999-99-99') ASC, created_at ASC",
            (case_id,),
        ).fetchall()

        searches = cur.execute(
            "SELECT * FROM search_runs WHERE case_id=? ORDER BY created_at ASC",
            (case_id,),
        ).fetchall()

        tags = cur.execute(
            """
            SELECT t.* FROM tags t
            JOIN case_tags ct ON ct.tag_id=t.id
            WHERE ct.case_id=?
            ORDER BY t.label ASC
            """,
            (case_id,),
        ).fetchall()

        tasks = cur.execute(
            """
            SELECT * FROM tasks
            WHERE case_id=?
            ORDER BY
              CASE status WHEN 'open' THEN 1 WHEN 'in_progress' THEN 2 WHEN 'blocked' THEN 3 WHEN 'done' THEN 4 ELSE 5 END,
              COALESCE(due_date, '9999-99-99') ASC,
              priority ASC,
              created_at ASC
            """,
            (case_id,),
        ).fetchall()

        docs = cur.execute(
            "SELECT * FROM documents WHERE case_id=? ORDER BY created_at ASC",
            (case_id,),
        ).fetchall()

    c = canvas.Canvas(str(out_path), pagesize=LETTER)
    w, h = LETTER
    margin = 0.75 * inch
    y = h - margin

    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin, y, "Reconnect — Case Packet")
    y -= 22
    c.setFont("Helvetica", 10)
    c.drawString(margin, y, f"Generated: {_now_utc()}")
    y -= 16

    # Case summary
    y = _section_title(c, "Case Summary", margin, y)
    summary_lines = [
        f"Case ID: {case_row['id']}",
        f"Title: {case_row['title']}",
        f"Subject: {case_row['subject_name']}",
        f"DOB: {case_row['dob'] or ''}",
        f"Aliases: {case_row['aliases'] or ''}",
        f"Last Known Locations: {case_row['last_known_locations'] or ''}",
        f"Relatives: {case_row['relatives'] or ''}",
    ]
    for line in summary_lines:
        y = _wrap_text(c, line, margin, y, w - 2 * margin, leading=13)

    if tags:
        y -= 4
        y = _wrap_text(
            c,
            "Tags: " + ", ".join([t["label"] for t in tags]),
            margin,
            y,
            w - 2 * margin,
            leading=13,
        )

    if case_row["notes"]:
        y -= 6
        y = _wrap_text(
            c, "Notes:", margin, y, w - 2 * margin, leading=13, font="Helvetica-Bold", size=11
        )
        y = _wrap_text(c, str(case_row["notes"]), margin, y, w - 2 * margin, leading=13)

    # Timeline
    y -= 8
    y = _section_title(c, "Timeline", margin, y)
    if not events:
        y = _wrap_text(c, "(No events yet)", margin, y, w - 2 * margin)
    else:
        for ev in events:
            if y < 1.2 * inch:
                c.showPage()
                y = h - margin
            date = ev["event_date"] or ""
            title = ev["title"] or ""
            etype = ev["event_type"] or ""
            y = _wrap_text(c, f"{date} — {etype}: {title}", margin, y, w - 2 * margin, leading=12)

    # Tasks
    y -= 8
    y = _section_title(c, "Tasks", margin, y)
    if not tasks:
        y = _wrap_text(c, "(No tasks yet)", margin, y, w - 2 * margin)
    else:
        for t in tasks:
            if y < 1.2 * inch:
                c.showPage()
                y = h - margin
            due = t["due_date"] or ""
            pr = t["priority"]
            status = t["status"]
            y = _wrap_text(
                c, f"[{status}] (P{pr}) {due} — {t['title']}", margin, y, w - 2 * margin, leading=12
            )
            if t["notes"]:
                y = _wrap_text(
                    c, f"Notes: {t['notes']}", margin + 14, y, w - 2 * margin - 14, leading=12
                )

    # Evidence
    y -= 8
    y = _section_title(c, "Evidence Items", margin, y)
    if not evidence:
        y = _wrap_text(c, "(No evidence yet)", margin, y, w - 2 * margin)
    else:
        # Citation Map keys: E1..En map to evidence items in this order.
        for i, it in enumerate(evidence, start=1):
            if y < 1.4 * inch:
                c.showPage()
                y = h - margin
            key = f"E{i}"
            date = it["event_date"] or ""
            kind = it["kind"]
            title = it["title"]
            c.setFont("Helvetica-Bold", 11)
            c.drawString(margin, y, f"{key}  {date}  [{kind}]  {title}")
            y -= 14
            c.setFont("Helvetica", 10)
            if it["url"]:
                y = _wrap_text(
                    c, f"URL: {it['url']}", margin + 14, y, w - 2 * margin - 14, leading=12
                )
            if it["content"]:
                y = _wrap_text(
                    c, f"Notes: {it['content']}", margin + 14, y, w - 2 * margin - 14, leading=12
                )
            if it["file_path"]:
                y = _wrap_text(
                    c, f"File: {it['file_path']}", margin + 14, y, w - 2 * margin - 14, leading=12
                )

    # Documents (generated outputs)
    y -= 8
    y = _section_title(c, "Generated Documents", margin, y)
    if not docs:
        y = _wrap_text(c, "(No generated documents yet)", margin, y, w - 2 * margin)
    else:
        for d in docs:
            if y < 1.4 * inch:
                c.showPage()
                y = h - margin
            y = _wrap_text(
                c,
                f"{d['created_at']} — {d['doc_type']}: {d['title']}",
                margin,
                y,
                w - 2 * margin,
                leading=12,
                font="Helvetica-Bold",
                size=10,
            )
            snippet = (d["content"] or "")[:600]
            if snippet:
                y = _wrap_text(
                    c, snippet.replace("\n", " "), margin + 14, y, w - 2 * margin - 14, leading=12
                )

    # Search runs
    y -= 8
    y = _section_title(c, "Search Runs", margin, y)
    if not searches:
        y = _wrap_text(c, "(No searches yet)", margin, y, w - 2 * margin)
    else:
        for sr in searches:
            if y < 1.2 * inch:
                c.showPage()
                y = h - margin
            y = _wrap_text(
                c,
                f"{sr['created_at']} — cached={bool(sr['cached'])}",
                margin,
                y,
                w - 2 * margin,
                leading=12,
                font="Helvetica-Bold",
                size=10,
            )
            try:
                q = json.loads(sr["query_json"])
                y = _wrap_text(
                    c,
                    "Query: " + json.dumps(q, ensure_ascii=False),
                    margin + 14,
                    y,
                    w - 2 * margin - 14,
                    leading=12,
                )
            except Exception:
                pass
            try:
                res = json.loads(sr["results_json"])
                y = _wrap_text(
                    c,
                    f"Results: {len(res)} linkouts",
                    margin + 14,
                    y,
                    w - 2 * margin - 14,
                    leading=12,
                )
            except Exception:
                pass

    c.showPage()
    c.save()
    return out_path

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List, Tuple

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")
URL_RE = re.compile(r"\bhttps?://[^\s<>\"]+\b", re.IGNORECASE)


def extract_entities(text: str) -> Dict[str, List[str]]:
    if not text:
        return {"email": [], "phone": [], "url": []}
    emails = sorted(set(EMAIL_RE.findall(text)))
    phones = sorted(set(PHONE_RE.findall(text)))
    urls = sorted(set(URL_RE.findall(text)))
    return {"email": emails, "phone": phones, "url": urls}


def build_case_graph(case_row: Dict[str, Any], evidence_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a lightweight graph (nodes/edges) from case and evidence."""
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []

    def add_node(node_id: str, label: str, ntype: str, meta: Dict[str, Any] | None = None):
        if node_id not in nodes:
            nodes[node_id] = {"id": node_id, "label": label, "type": ntype, "meta": meta or {}}

    def add_edge(src: str, dst: str, etype: str, weight: float = 1.0, meta: Dict[str, Any] | None = None):
        edges.append({"source": src, "target": dst, "type": etype, "weight": weight, "meta": meta or {}})

    subject_id = f"person:{case_row['subject_name']}"
    add_node(subject_id, case_row["subject_name"], "person", {"role": "subject"})

    # structured fields
    for alias in (case_row.get("aliases") or "").split(","):
        a = alias.strip()
        if a:
            nid = f"alias:{a}"
            add_node(nid, a, "alias")
            add_edge(subject_id, nid, "aka")

    for loc in (case_row.get("last_known_locations") or "").split(","):
        l = loc.strip()
        if l:
            nid = f"place:{l}"
            add_node(nid, l, "place")
            add_edge(subject_id, nid, "last_known")

    for rel in (case_row.get("relatives") or "").split(","):
        r = rel.strip()
        if r:
            nid = f"person:{r}"
            add_node(nid, r, "person", {"role": "relative"})
            add_edge(subject_id, nid, "related_to")

    # evidence nodes + derived entities
    for ev in evidence_rows:
        evid = f"evidence:{ev['id']}"
        add_node(evid, ev.get("title") or ev["id"], "evidence", {"kind": ev.get("kind"), "date": ev.get("event_date")})
        add_edge(subject_id, evid, "has_evidence", 0.5)

        blob = " ".join([str(ev.get("title") or ""), str(ev.get("url") or ""), str(ev.get("content") or "")])
        ents = extract_entities(blob)
        for kind, vals in ents.items():
            for v in vals:
                nid = f"{kind}:{v}"
                add_node(nid, v, kind)
                add_edge(evid, nid, f"mentions_{kind}", 1.0)

    return {"nodes": list(nodes.values()), "edges": edges}

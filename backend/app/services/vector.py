from __future__ import annotations

import base64
import hashlib
import json
import math
import re
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image
import io

from ..db import db_cursor
from ..utils import now_iso

TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _l2_normalize(v: List[float]) -> List[float]:
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


def hash_embed(text: str, dim: int = 512) -> List[float]:
    """Deterministic lightweight text embedding (offline)."""
    v = [0.0] * dim
    if not text:
        return v
    tokens = [t.lower() for t in TOKEN_RE.findall(text)][:8000]
    for tok in tokens:
        h = hash(tok)
        idx = h % dim
        v[idx] += 1.0
    return _l2_normalize(v)


def image_ahash_embed(image_bytes: bytes, hash_size: int = 8) -> Tuple[List[float], Dict[str, Any]]:
    """Average hash embedding for images (offline)."""
    img = Image.open(io.BytesIO(image_bytes)).convert("L")
    img = img.resize((hash_size, hash_size))
    pixels = list(img.getdata())
    avg = sum(pixels) / len(pixels)
    bits = [1.0 if p > avg else 0.0 for p in pixels]
    bitstring = "".join("1" if b > 0.5 else "0" for b in bits)
    hexstr = f"{int(bitstring, 2):016x}"
    return bits, {"ahash_hex": hexstr, "hash_size": hash_size}


def _vector_id(case_id: str, ref_type: str, ref_id: str, modality: str) -> str:
    key = f"{case_id}|{ref_type}|{ref_id}|{modality}".encode("utf-8")
    digest = hashlib.md5(key).hexdigest()[:20]
    return f"v_{digest}"


def upsert_vector(
    *,
    case_id: str,
    ref_type: str,
    ref_id: str,
    modality: str,
    vec: List[float],
    meta: Optional[Dict[str, Any]] = None,
) -> str:
    """Insert or replace a vector using a stable deterministic id."""
    vid = _vector_id(case_id, ref_type, ref_id, modality)
    dim = len(vec)
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO vectors(id, case_id, ref_type, ref_id, modality, dim, vec_json, meta_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              dim=excluded.dim,
              vec_json=excluded.vec_json,
              meta_json=excluded.meta_json,
              created_at=excluded.created_at
            """,
            (vid, case_id, ref_type, ref_id, modality, dim, json.dumps(vec), json.dumps(meta or {}), now_iso()),
        )
    return vid


def _cosine(a: List[float], b: List[float]) -> float:
    # assumes already normalized; if not, still works as dot-product similarity.
    return float(sum(x * y for x, y in zip(a, b)))


def query_similar(
    *,
    case_id: str,
    modality: str,
    vec: List[float],
    top_k: int = 8,
) -> List[Tuple[str, float, str, str, Dict[str, Any]]]:
    """Return [(vector_id, score, ref_type, ref_id, meta), ...]"""
    hits: List[Tuple[str, float, str, str, Dict[str, Any]]] = []
    with db_cursor() as cur:
        cur.execute(
            "SELECT id, ref_type, ref_id, vec_json, meta_json FROM vectors WHERE case_id=? AND modality=?",
            (case_id, modality),
        )
        rows = cur.fetchall()
    for r in rows:
        try:
            v = json.loads(r["vec_json"])
        except Exception:
            continue
        score = _cosine(vec, v)
        meta = {}
        try:
            meta = json.loads(r["meta_json"] or "{}")
        except Exception:
            meta = {}
        hits.append((r["id"], score, r["ref_type"], r["ref_id"], meta))
    hits.sort(key=lambda x: x[1], reverse=True)
    return hits[:top_k]

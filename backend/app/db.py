from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parents[1]  # backend/
DEFAULT_DATA_DIR = BASE_DIR / "data"

DB_PATH = Path(os.getenv("RECONNECT_DB", str(DEFAULT_DATA_DIR / "reconnect.db"))).resolve()
UPLOAD_DIR = Path(os.getenv("RECONNECT_UPLOAD_DIR", str(DEFAULT_DATA_DIR / "uploads"))).resolve()

# Note: Keep schema idempotent. Migrations below handle older DBs safely.
SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS cases (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  subject_name TEXT NOT NULL,
  dob TEXT,
  aliases TEXT,
  last_known_locations TEXT,
  relatives TEXT,
  notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  title TEXT NOT NULL,
  event_date TEXT,
  data_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_events_case_date ON events(case_id, event_date);

CREATE TABLE IF NOT EXISTS evidence_items (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL,
  kind TEXT NOT NULL,              -- link | note | file
  title TEXT NOT NULL,
  url TEXT,
  content TEXT,
  file_path TEXT,
  event_date TEXT,
  sensitive INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_evidence_case_date ON evidence_items(case_id, event_date);

CREATE TABLE IF NOT EXISTS search_cache (
  query_hash TEXT PRIMARY KEY,
  query_json TEXT NOT NULL,
  results_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON search_cache(expires_at);

CREATE TABLE IF NOT EXISTS search_runs (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL,
  query_json TEXT NOT NULL,
  results_json TEXT NOT NULL,
  sources_json TEXT NOT NULL,
  cached INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_search_case_time ON search_runs(case_id, created_at);

-- Vectors for lightweight local retrieval/similarity
CREATE TABLE IF NOT EXISTS vectors (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL,
  ref_type TEXT NOT NULL,          -- evidence | search_run | case | doc | task
  ref_id TEXT NOT NULL,
  modality TEXT NOT NULL,          -- text | image
  dim INTEGER NOT NULL,
  vec_json TEXT NOT NULL,
  meta_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_vectors_case ON vectors(case_id);
CREATE INDEX IF NOT EXISTS idx_vectors_ref ON vectors(ref_type, ref_id);
CREATE UNIQUE INDEX IF NOT EXISTS uidx_vectors_key ON vectors(case_id, ref_type, ref_id, modality);

-- Tags + joins (cases and evidence)
CREATE TABLE IF NOT EXISTS tags (
  id TEXT PRIMARY KEY,
  label TEXT NOT NULL UNIQUE,
  color TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS case_tags (
  case_id TEXT NOT NULL,
  tag_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY(case_id, tag_id),
  FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
  FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evidence_tags (
  evidence_id TEXT NOT NULL,
  tag_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY(evidence_id, tag_id),
  FOREIGN KEY(evidence_id) REFERENCES evidence_items(id) ON DELETE CASCADE,
  FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- Tasks
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',     -- open | in_progress | done | blocked
  due_date TEXT,
  priority INTEGER NOT NULL DEFAULT 2,     -- 1 high, 2 med, 3 low
  notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_tasks_case_status ON tasks(case_id, status);

-- Documents
CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL,
  doc_type TEXT NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_docs_case_time ON documents(case_id, created_at);

-- Optional full-text search (FTS5). If unavailable, app will fall back to LIKE.
"""

FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS fts_all USING fts5(
  case_id UNINDEXED,
  ref_type UNINDEXED,
  ref_id UNINDEXED,
  title,
  body,
  tokenize = 'porter'
);
"""

CREATE_AUDIT_SQL = """
CREATE TABLE IF NOT EXISTS audit_log (
  id TEXT PRIMARY KEY,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  case_id TEXT,
  meta_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(created_at);
"""


def ensure_dirs() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _table_info(cur: sqlite3.Cursor, table: str) -> Iterable[sqlite3.Row]:
    return cur.execute(f"PRAGMA table_info({table})").fetchall()


def _table_exists(cur: sqlite3.Cursor, table: str) -> bool:
    row = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    return row is not None


def _col_exists(cur: sqlite3.Cursor, table: str, col: str) -> bool:
    for r in _table_info(cur, table):
        if r["name"] == col:
            return True
    return False


def run_migrations(conn: sqlite3.Connection) -> None:
    """Best-effort migrations for older DBs."""
    cur = conn.cursor()

    # Ensure audit exists
    cur.executescript(CREATE_AUDIT_SQL)

    # Fix vectors table: add meta_json if missing, add unique index
    if _table_exists(cur, "vectors") and not _col_exists(cur, "vectors", "meta_json"):
        cur.execute("ALTER TABLE vectors ADD COLUMN meta_json TEXT")
    # Ensure indices
    cur.execute("CREATE INDEX IF NOT EXISTS idx_vectors_case ON vectors(case_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_vectors_ref ON vectors(ref_type, ref_id)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uidx_vectors_key ON vectors(case_id, ref_type, ref_id, modality)")

    # Create new tables if they weren't present (tags/tasks/docs)
    # (SCHEMA_SQL will create them too, but keeping here for older partial schema)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS tags (
      id TEXT PRIMARY KEY,
      label TEXT NOT NULL UNIQUE,
      color TEXT,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS case_tags (
      case_id TEXT NOT NULL,
      tag_id TEXT NOT NULL,
      created_at TEXT NOT NULL,
      PRIMARY KEY(case_id, tag_id),
      FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
      FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS evidence_tags (
      evidence_id TEXT NOT NULL,
      tag_id TEXT NOT NULL,
      created_at TEXT NOT NULL,
      PRIMARY KEY(evidence_id, tag_id),
      FOREIGN KEY(evidence_id) REFERENCES evidence_items(id) ON DELETE CASCADE,
      FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS tasks (
      id TEXT PRIMARY KEY,
      case_id TEXT NOT NULL,
      title TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'open',
      due_date TEXT,
      priority INTEGER NOT NULL DEFAULT 2,
      notes TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_tasks_case_status ON tasks(case_id, status);
    CREATE TABLE IF NOT EXISTS documents (
      id TEXT PRIMARY KEY,
      case_id TEXT NOT NULL,
      doc_type TEXT NOT NULL,
      title TEXT NOT NULL,
      content TEXT NOT NULL,
      created_at TEXT NOT NULL,
      FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_docs_case_time ON documents(case_id, created_at);
    """)

    # Try create FTS (optional)
    try:
        cur.executescript(FTS_SQL)
    except sqlite3.OperationalError:
        # FTS5 not available in this SQLite build; ignore.
        pass

    conn.commit()


def init_db() -> None:
    conn = get_conn()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.executescript(CREATE_AUDIT_SQL)
        # Attempt FTS create (optional)
        try:
            conn.executescript(FTS_SQL)
        except sqlite3.OperationalError:
            pass
        run_migrations(conn)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def db_cursor():
    conn = get_conn()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    finally:
        conn.close()

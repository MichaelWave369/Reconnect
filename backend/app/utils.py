from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional


def new_id(prefix: str = "") -> str:
    u = uuid.uuid4().hex
    return f"{prefix}{u}" if prefix else u


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def loads(s: Optional[str]) -> Any:
    if not s:
        return None
    return json.loads(s)

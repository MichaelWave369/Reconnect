from __future__ import annotations

import re

# Redaction is safety-first. Two modes:
# - default: mask phones/emails
# - sensitive/aggressive: additionally mask zips and long digit runs

PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")
EMAIL_RE = re.compile(r"\b[\w.%-]+@[\w.-]+\.[A-Za-z]{2,}\b")
ZIP_RE = re.compile(r"\b\d{5}(?:-\d{4})?\b")
LONG_DIGIT_RE = re.compile(r"\b\d{3,}\b")


def _mask_keep_last(text: str, keep: int = 2, mask_char: str = "•") -> str:
    if len(text) <= keep:
        return mask_char * len(text)
    return (mask_char * (len(text) - keep)) + text[-keep:]


def redact_text(s: str, aggressive: bool = False, sensitive: bool = False) -> str:
    """
    Backwards-compatible redactor.
    - aggressive=True is treated the same as sensitive=True.
    """
    if not s:
        return s

    mode_sensitive = bool(sensitive or aggressive)

    s = PHONE_RE.sub("[phone redacted]", s)
    s = EMAIL_RE.sub("[email redacted]", s)

    if mode_sensitive:
        s = ZIP_RE.sub("[zip redacted]", s)

        def repl(m: re.Match) -> str:
            token = m.group(0)
            if len(token) <= 4:
                return "•" * len(token)
            return _mask_keep_last(token, keep=2)

        s = LONG_DIGIT_RE.sub(repl, s)

    return s

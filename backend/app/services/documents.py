from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Tuple

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from ..utils import now_iso

SAFE_DOC_TYPES = {
    "welfare_check_script",
    "agency_letter",
    "dps_history_request",
    "timeline_affidavit",
    "presumed_death_petition",
}


@dataclass
class RenderedDoc:
    doc_type: str
    title: str
    content: str


def _fill(template: str, ctx: Dict[str, Any]) -> str:
    # simple {{key}} templating
    def repl(m):
        k = m.group(1).strip()
        return str(ctx.get(k, "")).strip()

    return re.sub(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}", repl, template)


def render_document(doc_type: str, ctx: Dict[str, Any]) -> RenderedDoc:
    if doc_type not in SAFE_DOC_TYPES:
        raise ValueError("Unknown doc_type")

    subject = ctx.get("subject_name", "Unknown")
    dob = ctx.get("dob", "")
    case_title = ctx.get("case_title", "Case")
    case_id = ctx.get("case_id", "")
    now = ctx.get("now", datetime.utcnow().strftime("%B %d, %Y"))

    base_ctx = dict(ctx)
    base_ctx.update(
        {
            "subject_name": subject,
            "dob": dob,
            "case_title": case_title,
            "case_id": case_id,
            "today": now,
        }
    )

    if doc_type == "welfare_check_script":
        title = "Welfare Check Call Script"
        template = """WELFARE CHECK REQUEST (PHONE SCRIPT)
Date: {{today}}

Hello—my name is {{requester_name}}. I’m calling to request a welfare check.

Person: {{subject_name}}
DOB: {{dob}}
Last known city/state: {{last_known_locations}}
Possible addresses: {{addresses}}

Relationship: {{requester_relation}}

Context (short): We have not heard from {{subject_name}} in approximately {{last_contact_year}} and we are seeking to confirm their welfare/status. We are not requesting any confidential information—only whether officers can confirm safety or advise next steps.

If you need follow-up:
Phone: {{requester_phone}}
Email: {{requester_email}}

Case reference (internal): {{case_id}} / {{case_title}}
"""
        return RenderedDoc(doc_type, title, _fill(template, base_ctx))

    if doc_type == "agency_letter":
        title = "Agency Letter (Status Inquiry)"
        template = """{{today}}

To Whom It May Concern,

My name is {{requester_name}}. I am writing regarding {{subject_name}} (DOB: {{dob}}). We have been unable to contact them since approximately {{last_contact_year}} and are attempting to confirm their welfare and/or status.

Last known locations: {{last_known_locations}}

If your agency has any non-confidential guidance on confirming whether an individual is deceased, in custody, hospitalized, or receiving services, we would be grateful. We understand that you may be unable to disclose private information; any direction on the appropriate public process is appreciated.

I can be reached at:
Phone: {{requester_phone}}
Email: {{requester_email}}

Sincerely,
{{requester_name}}
Relationship: {{requester_relation}}

Case reference (internal): {{case_id}} / {{case_title}}
"""
        return RenderedDoc(doc_type, title, _fill(template, base_ctx))

    if doc_type == "dps_history_request":
        title = "Arizona DPS Criminal History Request (Draft)"
        template = """ARIZONA DEPARTMENT OF PUBLIC SAFETY
CRIMINAL HISTORY RECORD REQUEST (DRAFT)

Date: {{today}}

Requester: {{requester_name}}
Relationship to subject: {{requester_relation}}
Contact: {{requester_phone}} / {{requester_email}}

Subject: {{subject_name}}
DOB: {{dob}}
Last known: {{last_known_locations}}

Purpose: Immediate family member requesting records to help determine welfare/status and resolve uncertainty after prolonged loss of contact.

Enclosures (recommended):
- Copy of requester photo ID
- Proof of relationship (e.g., birth certificate)
- Any required fees/forms per DPS instructions

Signature: ____________________________
Printed Name: {{requester_name}}
"""
        return RenderedDoc(doc_type, title, _fill(template, base_ctx))

    if doc_type == "timeline_affidavit":
        title = "Timeline Affidavit (Diligent Search)"
        template = """AFFIDAVIT OF DILIGENT SEARCH
Date: {{today}}

I, {{requester_name}}, declare under penalty of perjury that the following is true to the best of my knowledge:

1) I am the {{requester_relation}} of {{subject_name}} (DOB: {{dob}}).
2) Last known contact: approximately {{last_contact_year}}.
3) Last known locations: {{last_known_locations}}.
4) Diligent search actions taken:
   - Searched public death indexes and memorial sites
   - Checked public directories/addresses
   - Attempted contact with known relatives and associates
   - Reviewed public court/arrest records where available
   - Contacted local agencies for welfare checks (where appropriate)

5) Despite these efforts, we have been unable to confirm current status or location.

Signed: ____________________________
Printed Name: {{requester_name}}
Date: {{today}}

Case reference (internal): {{case_id}} / {{case_title}}
"""
        return RenderedDoc(doc_type, title, _fill(template, base_ctx))

    # presumed_death_petition (draft only; jurisdiction varies)
    title = "Presumed Death Petition (Draft — Verify Jurisdiction)"
    template = """IN THE SUPERIOR COURT OF THE STATE OF ARIZONA
IN AND FOR THE COUNTY OF MOHAVE

In the Matter of:
{{subject_name}}
DOB: {{dob}}

Case No.: __________________

PETITION FOR DECLARATION OF PRESUMED DEATH (DRAFT)

Petitioner: {{requester_name}}, {{requester_relation}} of the missing person.

1. Missing Person: {{subject_name}} (DOB: {{dob}}).
2. Last known locations: {{last_known_locations}}.
3. Last known contact: approximately {{last_contact_year}}.
4. Diligent search: Petitioner has conducted a diligent search including, but not limited to, public death indexes, memorial databases, public directories, and inquiries to known associates/relatives.
5. No evidence of life has been found after a prolonged period of absence.

WHEREFORE, Petitioner requests the Court enter an order declaring {{subject_name}} presumed deceased as of a date determined by the Court.

Respectfully submitted,

____________________________
{{requester_name}}
Date: {{today}}

NOTE: This is a draft template. Verify the correct statute and filing requirements with the court clerk or an attorney.
"""
    return RenderedDoc(doc_type, title, _fill(template, base_ctx))


def render_pdf_bytes(title: str, content: str) -> bytes:
    """Create a simple PDF from text."""
    from io import BytesIO

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    w, h = LETTER
    margin = 0.75 * inch
    y = h - margin

    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, y, title)
    y -= 18
    c.setFont("Helvetica", 9)

    for line in content.splitlines():
        if y < 1.0 * inch:
            c.showPage()
            y = h - margin
            c.setFont("Helvetica", 9)
        c.drawString(margin, y, line[:140])
        y -= 12

    c.showPage()
    c.save()
    return buf.getvalue()

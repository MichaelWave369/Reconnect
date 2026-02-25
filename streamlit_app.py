from __future__ import annotations

import streamlit as st
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

st.set_page_config(page_title="Reconnect", page_icon="🔎", layout="wide")
st.title("Reconnect")
st.caption("Local-first search helper (linkouts only, no scraping)")

with st.form("case_form"):
    st.subheader("Create Case")
    title = st.text_input("Case title", value="Find John Doe")
    subject_name = st.text_input("Subject name", value="John Doe")
    dob = st.text_input("DOB (optional)")
    aliases = st.text_input("Aliases (optional)")
    locations = st.text_input("Last known locations (optional)")
    relatives = st.text_input("Relatives (optional)")
    notes = st.text_area("Notes (optional)")
    submitted = st.form_submit_button("Create")

if submitted:
    create_resp = client.post(
        "/cases",
        json={
            "title": title,
            "subject_name": subject_name,
            "dob": dob or None,
            "aliases": aliases or None,
            "last_known_locations": locations or None,
            "relatives": relatives or None,
            "notes": notes or None,
        },
    )
    if create_resp.is_success:
        st.success(f"Created case {create_resp.json()['id']}")
    else:
        st.error(create_resp.text)

cases_resp = client.get("/cases")
cases = cases_resp.json() if cases_resp.is_success else []

st.subheader("Cases")
if not cases:
    st.info("No cases yet.")
else:
    selected = st.selectbox(
        "Select a case",
        cases,
        format_func=lambda item: f"{item['title']} ({item['id']})",
    )

    with st.form("evidence_form"):
        st.markdown("#### Add Evidence Note")
        ev_title = st.text_input("Evidence title", value="Lead")
        ev_content = st.text_area("Evidence content")
        sensitive = st.checkbox("Sensitive (redact phone/email/zip)", value=True)
        add_ev = st.form_submit_button("Add note")

    if add_ev:
        add_resp = client.post(
            f"/cases/{selected['id']}/evidence",
            json={
                "kind": "note",
                "title": ev_title,
                "content": ev_content,
                "sensitive": sensitive,
            },
        )
        if add_resp.is_success:
            st.success("Evidence note added.")
        else:
            st.error(add_resp.text)

    st.markdown("#### Run Search (linkouts)")
    search_name = st.text_input(
        "Search full name", value=selected["subject_name"], key="search_name"
    )
    if st.button("Run linkout search"):
        search_resp = client.post(
            f"/cases/{selected['id']}/search",
            json={
                "full_name": search_name,
                "dob": selected.get("dob"),
                "aliases": selected.get("aliases"),
                "location": selected.get("last_known_locations"),
                "relatives": selected.get("relatives"),
                "notes": selected.get("notes"),
                "local_only": True,
            },
        )
        if search_resp.is_success:
            for item in search_resp.json().get("results", []):
                st.markdown(f"- [{item['source']}]({item['url']})")
        else:
            st.error(search_resp.text)

    st.markdown("#### Evidence")
    ev_resp = client.get(f"/cases/{selected['id']}/evidence")
    if ev_resp.is_success:
        for ev in ev_resp.json():
            st.write(f"- **{ev['title']}** ({ev['kind']})")
            if ev.get("content"):
                st.code(ev["content"])

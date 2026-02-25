from __future__ import annotations

from pathlib import Path


def _new_case_payload() -> dict:
    return {
        "title": "Find Jane Doe",
        "subject_name": "Jane Doe",
        "dob": "1982-07-01",
        "aliases": "Janie",
        "last_known_locations": "Seattle, WA",
        "relatives": "John Doe",
        "notes": "Initial intake",
    }


def _create_case(client) -> str:
    response = client.post("/cases", json=_new_case_payload())
    assert response.status_code == 200
    return response.json()["id"]


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert isinstance(payload["version"], str)
    assert payload["version"]


def test_cases_crud(client):
    case_id = _create_case(client)

    list_response = client.get("/cases")
    assert list_response.status_code == 200
    assert any(item["id"] == case_id for item in list_response.json())

    update_payload = _new_case_payload() | {"title": "Updated Case Title"}
    update_response = client.patch(f"/cases/{case_id}", json=update_payload)
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated Case Title"

    delete_response = client.delete(f"/cases/{case_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["ok"] is True

    fetch_response = client.get(f"/cases/{case_id}")
    assert fetch_response.status_code == 404


def test_evidence_redaction_and_file_download(client, tmp_path: Path):
    case_id = _create_case(client)

    note_resp = client.post(
        f"/cases/{case_id}/evidence",
        json={
            "kind": "note",
            "title": "Sensitive lead",
            "content": "Call 206-555-1234 or jane@example.com in 98101.",
            "sensitive": True,
        },
    )
    assert note_resp.status_code == 200

    evidence_list = client.get(f"/cases/{case_id}/evidence")
    assert evidence_list.status_code == 200
    rendered = evidence_list.json()
    joined = "\n".join([item.get("content") or "" for item in rendered])
    assert "206-555-1234" not in joined
    assert "jane@example.com" not in joined
    assert "98101" not in joined

    upload_resp = client.post(
        f"/cases/{case_id}/evidence/upload",
        data={"title": "Upload Note", "sensitive": "false"},
        files={"file": ("note.txt", b"hello evidence", "text/plain")},
    )
    assert upload_resp.status_code == 200
    uploaded = upload_resp.json()
    assert uploaded["kind"] == "file"
    file_path = uploaded["file_path"]

    download_resp = client.get("/evidence/file", params={"path": file_path})
    assert download_resp.status_code == 200
    assert download_resp.content == b"hello evidence"

    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("blocked")
    blocked_resp = client.get("/evidence/file", params={"path": str(outside_file)})
    assert blocked_resp.status_code == 403


def test_search_is_linkout_only_and_network_free(client, monkeypatch):
    case_id = _create_case(client)
    called = {"count": 0}

    def fake_search(query: dict):
        called["count"] += 1
        return {
            "cached": False,
            "query_hash": "abc123",
            "results": [
                {
                    "source": "Test Source",
                    "category": "linkout",
                    "url": "https://example.org/search",
                    "notes": "No scraping",
                }
            ],
        }

    monkeypatch.setattr("app.main.run_linkout_search", fake_search)

    response = client.post(
        f"/cases/{case_id}/search",
        json={
            "full_name": "Jane Doe",
            "dob": "1982-07-01",
            "location": "Seattle, WA",
            "local_only": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert called["count"] == 1
    assert payload["results"][0]["url"].startswith("https://")
    assert payload["results"][0]["source"] == "Test Source"

# Reconnect — Find the People Who Matter

A **local-first, private case manager** to help you find someone you've lost contact with — a parent, a sibling, an old friend. Everything stays on your computer. Nothing is sent anywhere.

## What Reconnect Does

### 🧭 Guided First Steps Wizard
When you start a new search, Reconnect walks you through the process step by step — who you're looking for, what you remember, and who else might be connected. No experience needed.

### 🔍 Search Hub (40+ Databases)
Generates targeted links to over 40 databases across 12 categories:
- **Death Records & Indexes** — SSDI, FamilySearch, Find a Grave, BillionGraves, VA Gravesite Locator, Ancestry
- **Obituaries** — Legacy.com, Newspapers.com, Tributes.com, Echovita, direct Google search
- **Official Records** — County courts (Judyrecords), Federal Bureau of Prisons, state DOC, PACER, VINELink
- **People Search** — TruePeopleSearch, FastPeopleSearch, WhitePages, That's Them
- **Missing Persons** — NamUs, The Charley Project, The Doe Network, NCIC guidance
- **Unclaimed Assets** — MissingMoney.com, state treasurers, U.S. Treasury bonds, PBGC pensions, NAIC life insurance
- **Social Media** — Facebook, LinkedIn, broad social search
- **Genealogy** — Ancestry trees, MyHeritage, GEDmatch (DNA), FindMyPast
- **Property & Voter** — County property records, voter registration
- **Medical & Benefits** — Medicare/SSA guidance
- **News & Media** — Google News Archive

Each source includes priority ranking, search guidance, and "if found" action steps.

### 👥 Relationship Multiplier
When you list relatives or connected people, Reconnect automatically generates cross-reference searches. Relatives often appear in shared obituaries, property records, and court documents — searching for them can reveal information about the person you're looking for.

### 🏛️ State-Specific Records Guide
Enter a state and get the exact office, website, phone number, fees, processing times, and step-by-step instructions for requesting official death certificates, marriage records, and more. All 50 states + DC covered.

### 📋 Case Management
- Create and edit cases with structured fields (name, DOB, aliases, locations, relatives, notes)
- Per-case audit log (every action is tracked — useful as evidence of diligent search)
- Tags and tasks to organize your work
- Progress tracking with encouragement

### 📄 Document Templates
Generate draft documents for:
- Welfare check call scripts
- Agency letters (status inquiry)
- DPS criminal history requests
- Timeline affidavits (diligent search)
- Presumed death petitions

### 📊 Evidence Library
Save links, notes, and file uploads as you find them. Mark items as sensitive (auto-redact phone numbers, emails, zip codes). Everything is searchable and included in exports.

### 📑 PDF Case Packet Export
One-click export of your entire case — summary, timeline, evidence, searches, tasks, documents — as a professional PDF you can hand to an investigator, lawyer, or court clerk.

### 🤖 Local AI Summary (Optional)
If you run Ollama locally, Reconnect can generate an AI-powered case summary without sending any data to the cloud.

## Run It

### Quick Start (Windows, Mac, or Linux)

1. Open a terminal in the project folder:
```bash
cd reconnect/backend
```

2. Create and activate a virtual environment:
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# Mac/Linux
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Start Reconnect:
```bash
python main.py
```

Or run directly with uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> **Security note:** Reconnect binds to **localhost only** by default when using `python main.py`.
> To intentionally allow other devices on your network to access it, set `HOST=0.0.0.0`.

> **Reload note:** autoreload is disabled by default and is intended for local development only.
> Enable it with `RECONNECT_RELOAD=1` (it is forced off in Streamlit-managed runtimes).

5. Open your browser:
- **UI**: http://localhost:8000
- **API**: http://localhost:8000/health

### Optional: Enable AI Summaries
```bash
# Windows
set RECONNECT_OLLAMA=1
set OLLAMA_MODEL=llama3.1

# Mac/Linux
export RECONNECT_OLLAMA=1
export OLLAMA_MODEL=llama3.1
```
Requires [Ollama](https://ollama.ai) running locally.


### Streamlit (Optional)
```bash
streamlit run streamlit_app.py
```
This entrypoint does not run uvicorn and is safe for Streamlit Cloud environments.

### Docker (Optional)
```bash
docker compose up --build
```
Then open http://localhost:8000

## Security & Privacy

- **SQLite database**: `backend/data/reconnect.db`
- **Uploaded files**: `backend/data/uploads/`
- **No cloud, no API keys, no external calls** — everything stays on your machine
- **No scraping** — Reconnect generates search links that you click through yourself
- **Auto-redaction** — phones, emails, and zip codes are masked by default in the UI

## Safety & Legal

This app is designed for **lawful, family-welfare use**. It does not scrape websites, bypass logins, or violate any terms of service. The link-out approach means you're always searching through the official front door of each database.

The audit log creates a documented trail of your search efforts, which can be used as evidence of diligent search in legal proceedings (e.g., presumed death petitions, estate matters).

## Architecture

- **Backend**: Python / FastAPI / SQLite
- **Frontend**: Vanilla JS (no build step)
- **Optional AI**: Ollama (local LLM)
- **~4,000 lines** of focused, readable code

---

*Built with love for everyone searching for someone who matters to them.*


## Development

From `backend/`:

```bash
make dev    # install runtime + dev tooling
make lint   # ruff format check + lint
make test   # pytest
make run    # start app
```

Equivalent direct commands:

```bash
pip install -r requirements-dev.txt
ruff format --check .
ruff check .
pytest -q
python main.py
```

## Project Policies

Please read these before contributing:

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- [SECURITY.md](SECURITY.md)
- [RESPONSIBLE_USE.md](RESPONSIBLE_USE.md)

### Local data deletion

To remove all local case data and uploads, stop the app and delete `backend/data/`.

# Uploading Reconnect to GitHub (No Git Needed)

If your repo files appear as **one long line** on GitHub, it usually means the files were pasted into GitHub's editor (or line endings were altered).
The fix is to **upload the actual files** (not copy/paste) so GitHub keeps the real line breaks.

## Option A (Fastest): Delete the repo and re-upload cleanly
1. On GitHub, go to your repo → **Settings**
2. Scroll to the bottom → **Danger Zone**
3. Click **Delete this repository**
4. Recreate the repo with the same name: `Reconnect`
5. Use **Option B** below to upload the files

## Option B: Replace the repo contents using GitHub "Upload files" (recommended)
1. **Download this zip** and unzip it on your PC.
2. In GitHub (your repo), click **Add file → Upload files**
3. Drag-and-drop the **entire unzipped folder contents** into the upload area.
   - IMPORTANT: do **not** open files and paste their text into GitHub.
4. Scroll down → **Commit changes**

### Quick check
After uploading, click any of these files and confirm they show **many lines**:
- `backend/app/main.py`
- `docker-compose.yml`

## Run locally (Windows)
### Backend only
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```
Open: http://localhost:8000/health

### Docker (optional)
```powershell
docker compose up --build
```

If you want LAN access later:
- set `RECONNECT_HOST=0.0.0.0` (but only if you understand the privacy risk)

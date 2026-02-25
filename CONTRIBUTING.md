# Contributing

Thank you for helping improve Reconnect.

## Ground Rules
- **Privacy first**: never add telemetry, tracking, or cloud uploads by default.
- **No scraping**: Reconnect should remain a link-out tool unless a source explicitly allows automated access.
- **Safety-by-default**: keep localhost binding and redaction enabled.

## Dev Setup
```bash
cd backend
python -m venv .venv
# Windows: .\.venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Code Style
- Keep changes small and readable.
- Prefer standard library solutions.
- Add comments where behavior affects safety or privacy.

## Pull Requests
- Describe what changed and why.
- Include screenshots for UI changes.
- Note any security/privacy impact.

## License
By contributing, you agree your contributions are licensed under the MIT License.

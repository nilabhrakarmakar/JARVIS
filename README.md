# J.A.R.V.I.S.

A lightweight Flask + Groq AI assistant with Hinglish responses, personal memory, live information lookups, system stats, PDF/text attachments, and image understanding.

## What's new in the redesign

- Rebuilt the frontend as a responsive command-center UI.
- Removed the broken Google-login placeholder flow from the client.
- Hardened uploads with `secure_filename`, an allow-list, temporary files, and an 8 MB default limit.
- Removed shared global memory so one user's saved facts are not injected into another user's context.
- Moved runtime memory into `data/memory/` and added Git ignore rules so personal data is not committed.
- Made weather location configurable and support requests such as `weather in Delhi`.
- Reduced unnecessary live-data triggers.
- Added structured logging and production-safe Flask defaults (`debug` is off unless enabled explicitly).
- Removed the unused `duckduckgo-search` dependency.
- Added environment configuration through `.env` / deployment variables.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Set `GROQ_API_KEY` in your environment, then run:

```bash
python app.py
```

Open `http://127.0.0.1:5000`.

For production, use a WSGI server such as Gunicorn and keep `FLASK_DEBUG=0`.

## Configuration

See `.env.example`. Never commit real API keys or runtime memory files.

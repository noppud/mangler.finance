# Python Backend – Sheet Mangler

This is the Python backend for the Sheet Mangler project. It exposes:

- a FastAPI HTTP server (`/chat`), and
- a CLI chat client.

Both talk to OpenRouter and Google Sheets.

## 1. Environment variables

Create a local env file for the Python backend:

```bash
cd python_backend
cp .env.example .env.local  # or .env
```

Then edit `.env.local` (or `.env`) and set at least:

- `OPENROUTER_API_KEY` – your OpenRouter key
- optionally `DEFAULT_LLM_MODEL` (e.g. `anthropic/claude-3.5-sonnet`)
- optionally `GOOGLE_SERVICE_ACCOUNT_FILE` if you don't want to use the default key file path

The backend automatically loads env vars from (in this order):

1. `python_backend/.env.local`
2. `python_backend/.env`
3. repo root `.env.local`
4. repo root `.env`
5. `sheet-mangler/.env.local`

Existing shell env vars always win and are never overridden.

### Google service account key

The Sheets client uses a Google service account key JSON file.

- Use `python_backend/service-account.example.json` as a template.
- Copy it to `python_backend/service-account.json` and replace the placeholder values with the JSON you downloaded from Google Cloud.
- Alternatively, keep the key anywhere and point to it via the `GOOGLE_SERVICE_ACCOUNT_FILE` env var (absolute path recommended).

## 2. Virtualenv & dependencies

From the repo root:

```bash
cd python_backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Run the HTTP API (FastAPI)

From the repo root (with the virtualenv activated):

```bash
cd /Users/konstavaronen/fintech-2
source python_backend/.venv/bin/activate
uvicorn python_backend.api:app --reload --port 8000
```

The API will be available at `http://localhost:8000/chat`.
Request/response examples live in `python_backend/API_USAGE.md`.

## 4. Run the CLI chat client

From the repo root (with the virtualenv activated):

```bash
cd /Users/konstavaronen/fintech-2
source python_backend/.venv/bin/activate
python -m python_backend.cli
```

You can optionally specify:

- `--session-id` – reuse a conversation
- `--sheet-id` and `--sheet-title` – to give the assistant sheet context

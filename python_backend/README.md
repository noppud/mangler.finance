# Sheet Mangler – Python Backend

This directory contains the Python backend for the Sheet Mangler project.  
It provides:

- a FastAPI HTTP server (`/chat` and `/tools/*`), and  
- a CLI chat client.

Both use OpenRouter for LLM calls and the Google Sheets API to inspect, modify, and create spreadsheets.

---

## What this backend can do

- **Chat with an AI assistant** about your spreadsheets via `POST /chat`.
- **Detect issues** in a sheet (formula errors, type mismatches, missing data, etc.) using rule‑based checks plus LLM analysis.
- **Modify existing sheets** (add/rename columns, update formulas, normalize/clear data, set values) via an LLM‑generated plan.
- **Create new spreadsheets** from a natural‑language description, with structured tabs, columns, example rows, and a README sheet.
- **Highlight and restore cell colors** in Google Sheets using `/tools/color` and `/tools/restore` (with Supabase‑backed snapshots).
- **Update and undo cell values** via `/tools/update_cells` and `/tools/restore_cells` with automatic value snapshots in Supabase.
- **Maintain conversation memory** per `sessionId` in‑memory, plus **optional Supabase persistence** of all messages.
- **Run interactively from the terminal** via a simple Python CLI.

For detailed API request/response examples, see `python_backend/API_USAGE.md`.

---

## 1. Prerequisites

- Python 3.11+ (or a recent 3.x that works with FastAPI & Pydantic v2).
- An **OpenRouter** API key.
- A **Google Cloud service account** with access to Google Sheets and Drive (for reading/writing spreadsheets).
- Optional: a **Supabase** project if you want to persist chat history and snapshot data.

---

## 2. Environment configuration

Create a local env file for the Python backend:

```bash
cd python_backend
cp .env.example .env.local  # or .env
```

Then edit `.env.local` (or `.env`) and set at least:

- `OPENROUTER_API_KEY` – your OpenRouter key (required)
- optional model & OpenRouter config:
  - `DEFAULT_LLM_MODEL` (e.g. `anthropic/claude-3.5-sonnet` or `anthropic/claude-haiku-4.5`)
  - `OPENROUTER_SITE_URL`
  - `OPENROUTER_SITE_NAME`
  - `OPENROUTER_BASE_URL`
- optional Google Sheets config:
  - `GOOGLE_SERVICE_ACCOUNT_FILE` – path to the JSON key file (absolute path recommended), **or**
  - `GOOGLE_SERVICE_ACCOUNT_JSON` – raw JSON content of the key
- optional Supabase config (for conversation & snapshot persistence):
  - `SUPABASE_URL`
  - one of: `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_SERVICE_KEY`, or `SUPABASE_ANON_KEY`

The backend automatically loads env vars from local `.env`‑style files (without overriding existing shell variables), in this order:

1. `python_backend/.env.local`
2. `python_backend/.env`
3. repo root `.env.local`
4. repo root `.env`
5. `sheet-mangler/.env.local` (if present)

You can still export variables directly in your shell; exported values always win.

### Google service account key

The Sheets client uses a Google service account key JSON file.

You can provide it in either of two ways:

1. **Env var JSON (recommended for hosted environments):**
   - Set `GOOGLE_SERVICE_ACCOUNT_JSON` to the raw JSON contents of your key.

2. **Key file on disk:**
   - Use `python_backend/service-account.example.json` as a template.
   - Copy it to `python_backend/service-account.json` and replace the placeholder values with your downloaded key JSON.
   - Or place the key anywhere and point to it via `GOOGLE_SERVICE_ACCOUNT_FILE`.

If neither is found, the backend will raise an error when it tries to access Google Sheets.

---

## 3. Virtualenv & dependencies

From the repo root:

```bash
cd python_backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

If you want to persist conversations to Supabase, also make sure your Supabase
database has been migrated (see **6. Conversation persistence (Supabase)**).

---

## 4. Run the HTTP API (FastAPI)

From the repo root (with the virtualenv activated):

```bash
cd /Users/konstavaronen/fintech-2   # or your cloned repo root
source python_backend/.venv/bin/activate
uvicorn python_backend.api:app --reload --port 8000
```

The API will be available at:

- `http://localhost:8000/chat` – main chat endpoint  
- `http://localhost:8000/docs` – automatically generated FastAPI docs (Swagger UI)

Request/response examples live in `python_backend/API_USAGE.md`.

You can also run the app using the small `main.py` wrapper:

```bash
cd /Users/konstavaronen/fintech-2
source python_backend/.venv/bin/activate
python -m python_backend.main
```

This uses `uvicorn` under the hood and listens on `PORT` (default `8000`).

---

## 5. Run the CLI chat client

From the repo root (with the virtualenv activated):

```bash
cd /Users/konstavaronen/fintech-2
source python_backend/.venv/bin/activate
python -m python_backend.cli
```

You can optionally specify:

- `--session-id` – reuse a conversation across runs (defaults to a random UUID)
- `--sheet-id` – Google Sheets spreadsheet ID or full URL
- `--sheet-title` – sheet/tab name

Example:

```bash
python -m python_backend.cli \
  --session-id my-session-123 \
  --sheet-id "1ABC...XYZ" \
  --sheet-title "Transactions"
```

---

## 6. Conversation memory & persistence (Supabase)

### In‑memory conversation store

By default, the backend maintains in‑memory conversation history per `sessionId` using
`ConversationStore`. This is used by both the HTTP API and the CLI.  
If you omit `sessionId` in `ChatRequest`, the backend behaves statelessly.

### Persisting conversations to Supabase

If Supabase is configured via environment variables, every chat message is
also stored with a lightweight relational structure:

- `sheet_tabs` – one row per Google Sheet tab:
  - `id` – UUID primary key
  - `spreadsheet_id` – raw Sheets ID (e.g. `1ABC...XYZ`)
  - `spreadsheet_url` – full Sheets URL (derived from ID if only ID is provided)
  - `sheet_title` – tab name
  - `created_at`

- `conversation_messages` – one row per message:
  - `id` – UUID primary key
  - `session_id` – the `sessionId` from the request or CLI session
  - `message_id` – the `ChatMessage.id` value (unique)
  - `role` – `"user" | "assistant" | "tool" | "system"`
  - `content` – message text
  - `metadata` – JSON blob of `ChatMessage.metadata`
  - `sheet_tab_id` – optional foreign key to `sheet_tabs.id` (set when sheet context is present)
  - `created_at` – timestamp

The logger derives sheet information from `ChatRequest.sheetContext` / `SheetContext`
whenever both `spreadsheetId` and `sheetTitle` are provided:

- If `spreadsheetId` is a full URL, the spreadsheet ID is parsed from `/d/...`.
- If it’s just an ID, a canonical URL is generated.

To set this up:

1. Apply the SQL migrations in `python_backend/migrations` to your Supabase
   Postgres database, in order:

   ```bash
   # From repo root, adjust to your own migration tooling
   psql "$SUPABASE_DB_URL" -f python_backend/migrations/001_create_conversation_messages.sql
   psql "$SUPABASE_DB_URL" -f python_backend/migrations/002_add_sheet_tabs.sql
   ```

2. Set the Supabase environment variables for the Python backend as described
   above (`SUPABASE_URL` and key).

If Supabase is not configured or unavailable, the logger is a no‑op and the
backend continues to work with in‑memory‑only conversations.

---

## 7. Google Sheets tool endpoints

In addition to `/chat`, the FastAPI app exposes a few utility endpoints used by the Sheet Mangler UI and tools:

- `POST /tools/color`  
  Apply background colors (and optional notes) to one or more cell ranges in a default spreadsheet.  
  Before coloring, the current colors are snapshotted to Supabase so they can be restored.

- `POST /tools/restore`  
  Restore cell background colors from a previously stored color snapshot batch.

- `POST /tools/update_cells`  
  Batch update cell values (or formulas) in a spreadsheet. Supports:
  - single cells or ranges
  - formula vs value inputs
  - automatic value snapshots to Supabase for undo via `snapshot_batch_id`

- `POST /tools/restore_cells`  
  Restore cell values from a `snapshot_batch_id` created by `/tools/update_cells`.

These endpoints expect Supabase and Google Sheets to be configured. Errors are returned as standard FastAPI HTTP errors.

---

## 8. Deployment options

### Docker

This backend includes a Dockerfile and `docker-compose.yml`.  
See `python_backend/README.Docker.md` for container‑based setup and configuration.

### Railway

This backend can be deployed to [Railway](https://railway.com) using the default
**Railpack** builder.

- The FastAPI app lives in `python_backend/api.py` as `app`.
- The repo root contains `main.py` which exposes that app as `app` at
  the root module level and, when run directly, starts Uvicorn.
- The root `requirements.txt` should include this backend’s dependencies so
  Railpack can install everything.

To deploy with Railpack:

1. Push this repository (with the `python_backend` directory) to GitHub or another Git provider.
2. Create a new **Service** in Railway, connecting it to this repo.
3. In the service settings:
   - Set the **Builder** to **Railpack** (default).
   - Set the **Root Directory** to `.` (the repo root) so Railpack sees
     `requirements.txt` and `main.py`.
4. Ensure the required environment variables are set in Railway
   (see **2. Environment configuration** above).

Railpack will install dependencies and either:

- detect FastAPI and run `uvicorn` against `main:app`, or
- run `python main.py`, which starts Uvicorn on `$PORT`.

Either way, the `/chat` endpoint will be available on the Railway‑generated URL.

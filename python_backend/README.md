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
- optionally Supabase config to persist conversations:
  - `SUPABASE_URL`
  - one of: `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_SERVICE_KEY`, or `SUPABASE_ANON_KEY`

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

If you want to persist conversations to Supabase, also make sure your Supabase
database has been migrated (see **6. Conversation persistence (Supabase)**).

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

## 5. Conversation memory

The backend maintains in-memory conversation history per `sessionId` using
`ConversationStore`. This is used by both the HTTP API and the CLI helper.

## 6. Conversation persistence (Supabase)

If Supabase is configured via environment variables, every chat message is
also stored with lightweight relational structure:

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

If Supabase is not configured or unavailable, the logger is a no-op and the
backend continues to work with in-memory-only conversations.

## 7. Deploying to Railway

This backend is configured to be deployable to [Railway](https://railway.com) using
their FastAPI / config-as-code flow.

- The FastAPI app lives in `python_backend/api.py` as `app`.
- `python_backend/railway.json` configures Railway to use the Nixpacks builder and
  start the server with:

  ```bash
  hypercorn api:app --bind "[::]:$PORT"
  ```

To deploy:

1. Push this repository (with the `python_backend` directory) to GitHub or another Git provider.
2. Create a new **Service** in Railway, connecting it to this repo.
3. In the service settings, set the **Root Directory** to `python_backend` so Railway
   uses this folder as the project root (where `requirements.txt` and `railway.json` live).
4. Ensure the required environment variables for this backend are set in Railway
   (see **1. Environment variables** above).

After the first deploy, Railway will build from `requirements.txt` and start
`hypercorn api:app` on the port defined by `$PORT`. The `/chat` endpoint will be
available on the Railway-generated URL.

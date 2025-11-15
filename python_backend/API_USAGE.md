# Python Chat API (FastAPI) – Usage Examples

This backend exposes a single HTTP endpoint for chat-style interactions with Google Sheets tools.

- Base URL (local dev): `http://localhost:8000`
- Endpoint: `POST /chat`

The server must be running first:

```bash
cd /Users/konstavaronen/fintech-2
source python_backend/.venv/bin/activate
uvicorn python_backend.api:app --reload --port 8000
```

Make sure these environment variables are set in the same shell:

- `OPENROUTER_API_KEY` – your OpenRouter key
- `DEFAULT_LLM_MODEL` – e.g. `anthropic/claude-3.5-sonnet`
- Optional: `GOOGLE_SERVICE_ACCOUNT_FILE` – overrides the default service-account JSON path

The service-account JSON must be accessible to the backend (see `python_backend/sheets_client.py` for lookup order).

---

## Request / Response Shape

Endpoint:

```text
POST /chat
Content-Type: application/json
Accept: application/json
```

Request body (`ChatRequest`):

```jsonc
{
  "messages": [
    {
      "id": "uuid-or-any-string",
      "role": "user",          // "user" | "assistant" | "tool" | "system"
      "content": "Hello",
      "metadata": null         // optional
    }
  ],
  "sheetContext": {
    "spreadsheetId": "1ABC...XYZ or full Sheets URL (optional)",
    "sheetTitle": "Sheet1 (optional)"
  },
  "sessionId": "my-session-123" // optional; enables conversation memory
}
```

Response body (`ChatResponse`):

```jsonc
{
  "messages": [
    {
      "id": "generated-id",
      "role": "assistant" | "tool",
      "content": "assistant or tool response",
      "metadata": {
        "toolName": "detect_issues" | "modify_sheet" | "create_sheet",
        "payload": { "tool-specific": "structured result" }
      }
    }
  ],
  "sessionId": "my-session-123"
}
```

The backend only returns *new* messages for this turn, not the full history.

---

### Quick sanity check request

To verify the API and LLM wiring without any sheet context or memory, you can use this minimal request:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "id": "test-1",
        "role": "user",
        "content": "Hello",
        "metadata": null
      }
    ]
  }'
```

If everything is configured correctly (environment variables, OpenRouter key, model), this should return a normal `assistant` message rather than an error.

---

## 1. Simple Stateless Chat (no memory, no Sheets)

You can call the endpoint without `sessionId` or sheet context for a pure conversational reply:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "id": "1",
        "role": "user",
        "content": "Hi Sheet Mangler, what can you do?",
        "metadata": null
      }
    ],
    "sheetContext": {
      "spreadsheetId": "",
      "sheetTitle": ""
    }
  }'
```

This will return one or more assistant messages. No cross-request memory is kept because `sessionId` is omitted.

---

## 2. Chat with Conversation Memory

Use a stable `sessionId` across requests to enable in-memory conversation history:

```bash
SESSION_ID="demo-session-1"

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"messages\": [
      {
        \"id\": \"1\",
        \"role\": \"user\",
        \"content\": \"Let’s talk about spreadsheets.\",
        \"metadata\": null
      }
    ],
    \"sheetContext\": {
      \"spreadsheetId\": \"\",
      \"sheetTitle\": \"\"
    },
    \"sessionId\": \"${SESSION_ID}\"
  }"
```

Then send a follow-up in the same session:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"messages\": [
      {
        \"id\": \"2\",
        \"role\": \"user\",
        \"content\": \"What did I just ask you about?\",
        \"metadata\": null
      }
    ],
    \"sheetContext\": {
      \"spreadsheetId\": \"\",
      \"sheetTitle\": \"\"
    },
    \"sessionId\": \"${SESSION_ID}\"
  }"
```

The backend stores all prior messages for `demo-session-1` in memory and includes them when deciding how to respond.

---

## 3. Detect Issues in a Google Sheet

Example: ask the assistant to run the `detect_issues` tool on a sheet. The LLM decides when to call tools; you just specify the sheet context and natural-language request.

```bash
SHEET_ID="1ABC...XYZ"        # or full Sheets URL
SHEET_TITLE="Transactions"   # sheet/tab name

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"messages\": [
      {
        \"id\": \"1\",
        \"role\": \"user\",
        \"content\": \"Scan my sheet for issues and inconsistencies.\",
        \"metadata\": null
      }
    ],
    \"sheetContext\": {
      \"spreadsheetId\": \"${SHEET_ID}\",
      \"sheetTitle\": \"${SHEET_TITLE}\"
    },
    \"sessionId\": \"sheet-audit-1\"
  }"
```

The response will typically include:

- A `tool` message with `metadata.toolName = "detect_issues"` and a structured `payload` containing detected issues.
- An `assistant` message summarizing the findings.

---

## 4. Modify a Sheet

Ask the assistant to modify an existing sheet; it will plan changes and execute supported actions:

```bash
SHEET_ID="1ABC...XYZ"
SHEET_TITLE="Transactions"

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"messages\": [
      {
        \"id\": \"1\",
        \"role\": \"user\",
        \"content\": \"Add a Total column that sums all numeric columns per row.\",
        \"metadata\": null
      }
    ],
    \"sheetContext\": {
      \"spreadsheetId\": \"${SHEET_ID}\",
      \"sheetTitle\": \"${SHEET_TITLE}\"
    },
    \"sessionId\": \"sheet-modify-1\"
  }"
```

The `tool` message’s `metadata.payload` will include:

- `plan`: the LLM-generated modification plan.
- `executedActions`: what was actually applied.
- `errors` (if any).

---

## 5. Create a New Spreadsheet

Ask the assistant to create a brand new spreadsheet based on a description:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "id": "1",
        "role": "user",
        "content": "Create a budget tracker with income, expenses, and a summary sheet.",
        "metadata": null
      }
    ],
    "sheetContext": {
      "spreadsheetId": "",
      "sheetTitle": ""
    },
    "sessionId": "sheet-create-1"
  }'
```

The `tool` message will include a `payload.plan` (design) and `payload.spreadsheetId`, and the assistant summary includes a direct URL to the new sheet.

---

## 6. Using the Python CLI Instead of HTTP

You can also use the CLI wrapper which talks to the same backend logic:

```bash
cd /Users/konstavaronen/fintech-2
source python_backend/.venv/bin/activate

python -m python_backend.cli \
  --session-id my-session-123 \
  --sheet-id "1ABC...XYZ" \
  --sheet-title "Transactions"
```

Then type messages at the `You:` prompt. The CLI uses the same in-memory conversation store and tools as the HTTP `/chat` endpoint.

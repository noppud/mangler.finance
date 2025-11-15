# Sheet Mangler – Agentic Chat SPA Refactor Plan

This document outlines how to refactor Sheet Mangler from a tab-based UI into a single-window, agentic chat SPA where all actions (detect issues, modify sheet, create sheet) are driven through one chat interface.

---

## 1. Product / UX Goals

- Single chat interface where the user:
  - Configures the target spreadsheet (URL/ID + sheet title).
  - Describes goals in natural language.
  - Sees what the agent plans to do, what tools it runs, and the results.
- Agent can:
  - Detect issues in a sheet.
  - Modify an existing sheet.
  - Create a new sheet.
  - Ask clarifying questions if required context is missing.
- Phase 1: in-memory chat only (no DB).
- Phase 2: optional Supabase-backed session history and multi-device persistence.

---

## 2. High-Level Architecture

- **Frontend**
  - Next.js App Router (existing).
  - Replace tabbed `Detect / Modify / Create` view with a single Chat page.
  - Reuse existing feature UIs as embedded “attachments” inside chat messages.
- **Backend**
  - New unified `/api/chat` endpoint.
  - New `AgentOrchestrator` that:
    - Uses the existing LLM client.
    - Calls existing agents (`MistakeDetector`, `SheetModifier`, `SheetCreator`) as tools.
- **Optional Persistence (Phase 2)**
  - Supabase for sessions and messages.

---

## 3. Frontend Refactor

### 3.1 New Chat Page

- **File**: `app/page.tsx`
- Replace the tab logic with a chat-first layout:
  - Header (existing branding).
  - Main area:
    - Left/center: scrollable chat transcript.
    - Top or side: “Sheet context” panel for spreadsheet URL/ID + sheet title.
    - Bottom: `ChatInput` component (multi-line text area + send button).
- Keep existing color palette and card styles for visual consistency.

### 3.2 Chat State Model

- Define a `ChatMessage` type:
  - `id: string`
  - `role: 'user' | 'assistant' | 'tool' | 'system'`
  - `content: string`
  - `metadata?: { toolName?: 'detect_issues' | 'modify_sheet' | 'create_sheet'; payload?: any }`
- Introduce a `useChat` hook or local state in `app/page.tsx`:
  - `messages: ChatMessage[]`
  - `sheetContext: { spreadsheetId?: string; sheetTitle?: string }`
  - Actions:
    - `addUserMessage(content)`
    - `addAssistantMessage(content, metadata?)`
    - `addToolMessage(toolName, payload)`
    - `setSheetContext({ spreadsheetId, sheetTitle })`
    - `resetConversation()`

### 3.3 Chat UI Components

- **`ChatTranscript`**
  - Displays all messages in order.
  - Auto-scrolls to bottom on new messages.
  - Groups consecutive messages from same role visually.

- **`ChatMessageBubble`**
  - Renders:
    - User messages (right-aligned).
    - Assistant messages (left-aligned).
    - Tool messages with rich content (cards).
  - For `tool` messages:
    - When `toolName === 'detect_issues'`, render issues using existing Detect UI.
    - When `toolName === 'modify_sheet'`, render plan/actions/warnings/errors using existing Modify UI.
    - When `toolName === 'create_sheet'`, render “sheet created” summary using existing Create UI.

- **`ChatInput`**
  - Multi-line text area.
  - `Enter` sends (with optional `Shift+Enter` for newline).
  - Disabled while a request is in flight.

### 3.4 Sheet Context Capture

- Add a small panel at the top or side of the chat:
  - Fields:
    - `Spreadsheet URL/ID` (single field; ID is extracted server-side).
    - `Sheet Title` (optional but recommended).
  - This updates `sheetContext` state.
- The agent can also ask for missing context via chat if a tool call requires it.

---

## 4. Frontend → Backend API Contract

### 4.1 Request Shape

- New endpoint: `POST /api/chat`
- Body:

```json
{
  "messages": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ],
  "sheetContext": {
    "spreadsheetId": "https://docs.google.com/...",
    "sheetTitle": "Taulukko1"
  },
  "sessionId": "optional-session-id-for-future-persistence"
}
```

### 4.2 Response Shape

- Example response:

```json
{
  "messages": [
    {
      "role": "tool",
      "toolName": "detect_issues",
      "payload": {
        "issues": [ /* existing MistakeDetector result */ ],
        "summary": "..."
      }
    },
    {
      "role": "assistant",
      "content": "I analyzed your sheet and found 2 critical issues...",
      "metadata": {
        "plan": "Short natural language explanation of what was done."
      }
    }
  ]
}
```

- The frontend:
  - Appends each returned message to local state in order.
  - Uses `toolName` and `payload` to render rich cards.

---

## 5. Backend: Unified Chat / Agent Endpoint

### 5.1 New `AgentOrchestrator`

- **File**: `lib/agents/assistant.ts` (new)
- Responsibilities:
  - Accept chat history and `sheetContext`.
  - Use `createLLMClient()` with a new `AGENT` prompt.
  - Decide whether to:
    - Respond directly as assistant.
    - Call a tool:
      - `detect_issues`
      - `modify_sheet`
      - `create_sheet`
  - Map tool calls to existing agents:
    - `MistakeDetector.detectIssues(spreadsheetId, sheetTitle, config)`
    - `SheetModifier.modify(modRequest)`
    - `SheetCreator.create(createRequest)`
  - Return tool outputs + assistant summaries to the API route.

### 5.2 Tool Call Protocol

- Use a strict JSON schema for the LLM with `chatJSON`:

```json
{
  "step": "answer" | "tool_call",
  "assistantMessage": "string",
  "tool": {
    "name": "detect_issues" | "modify_sheet" | "create_sheet",
    "arguments": { "spreadsheetId": "string", "sheetTitle": "string?", "prompt": "string?", "constraints": { } }
  }
}
```

- For `step === "tool_call"`:
  - Validate required args:
    - `detect_issues`: `spreadsheetId`, `sheetTitle`.
    - `modify_sheet`: `spreadsheetId`, `prompt`; optional `sheetTitle`, `constraints`.
    - `create_sheet`: `prompt`; optional `constraints`.
  - Normalize `spreadsheetId` using `normalizeSpreadsheetId`.
  - Call the appropriate agent.
  - Construct:
    - A `tool` message (for the frontend to render).
    - A follow-up assistant message summarizing results.

### 5.3 `/api/chat` Route

- **File**: `app/api/chat/route.ts` (new)
- `POST` handler:
  - Parse `messages`, `sheetContext`, `sessionId`.
  - Initialize shared dependencies:
    - `ServiceAccountSheetsClient`
    - `ContextBuilder`
    - `createLLMClient()`
    - `MistakeDetector`, `SheetModifier`, `SheetCreator`, `AgentOrchestrator`
  - Pass the request to `AgentOrchestrator`.
  - Return `{ messages: [...] }` per the contract above.
- Error handling:
  - Map `404`-style errors similarly to existing `/api/sheets/*` routes.
  - Return structured errors that can be rendered as assistant messages.

---

## 6. Agent Prompt Design

### 6.1 New `AGENT` Prompt

- **File**: `lib/llm/prompts.ts`
- Add `PROMPTS.AGENT` with:
  - Role description:
    - “You are Sheet Mangler, an AI assistant for working with Google Sheets via detection, modification, and creation tools.”
  - Tools:
    - `detect_issues(spreadsheetId, sheetTitle, config?)`
    - `modify_sheet(spreadsheetId, sheetTitle?, prompt, constraints?)`
    - `create_sheet(prompt, constraints?)`
  - Behavioral guidelines:
    - Ask for missing spreadsheet ID or sheet title when needed.
    - Prefer running `detect_issues` before risky modifications.
    - Explain in plain language what you plan to do before/after tool use.
  - Output format:
    - Always respond with **JSON only**, following the schema in section 5.2.
    - If answering conversationally without tools, set `step: "answer"` and include `assistantMessage`.

### 6.2 Multi-Step Interactions (Optional)

- Later enhancement:
  - Allow the model to propose multiple sequential tool calls in one response (e.g., detect → modify).
  - Implement a simple loop in `AgentOrchestrator`:
    - While response is `tool_call`, execute tool, append tool result to internal “conversation”, and re-query the LLM, up to a safety limit.

---

## 7. Supabase Integration (Phase 2 – Optional)

### 7.1 Schema

- **Table `sessions`**
  - `id` (uuid, PK)
  - `user_id` (uuid or text, depending on auth)
  - `created_at`, `last_message_at`
  - `title` (e.g., first user message or sheet name)
  - `spreadsheet_id`, `sheet_title`

- **Table `messages`**
  - `id` (uuid, PK)
  - `session_id` (FK to `sessions.id`)
  - `role` (`user`, `assistant`, `tool`, `system`)
  - `content` (text)
  - `tool_name` (nullable)
  - `tool_payload` (jsonb, nullable)
  - `created_at`

### 7.2 API Changes

- Extend `POST /api/chat`:
  - Accept `sessionId`.
  - If provided:
    - Load prior messages from Supabase when needed (or assume frontend sends full history).
    - Append new messages and tool outputs to `messages` table.
  - If not provided:
    - Create a new `sessions` row on first message.
    - Return `sessionId` to the client.

- Add helper routes:
  - `GET /api/sessions` – list recent sessions for the current user.
  - `GET /api/sessions/[id]/messages` – fetch a session’s message history.

### 7.3 Frontend Changes

- On app load:
  - Create or load a `sessionId` (URL param or localStorage).
  - Pass `sessionId` with every `/api/chat` call.
- Add a sidebar (optional) with:
  - List of previous sessions.
  - Click to load a session and its message history into the chat view.

---

## 8. Migration & Implementation Steps

1. **Scaffold Chat UI**
   - Refactor `app/page.tsx` to show a basic chat layout (no backend yet).
   - Implement `ChatTranscript`, `ChatMessageBubble`, and `ChatInput` with fake responses.

2. **Extract / Reuse Existing Feature UIs**
   - Move display logic from:
     - `components/features/DetectIssues.tsx`
     - `components/features/ModifySheet.tsx`
     - `components/features/CreateSheet.tsx`
   - Into smaller subcomponents that can be rendered inside a `tool` chat bubble.
   - Keep existing API calls for now for reference.

3. **Implement `AgentOrchestrator`**
   - Add `lib/agents/assistant.ts` with the protocol described above.
   - Integrate existing agents (`MistakeDetector`, `SheetModifier`, `SheetCreator`).
   - Implement tool calling, error handling, and simple assistant summarization.

4. **Create `/api/chat` Endpoint**
   - Add `app/api/chat/route.ts`.
   - Wire it to `AgentOrchestrator`.
   - Mirror error handling patterns from the existing `/api/sheets/*` routes.

5. **Wire Frontend to `/api/chat`**
   - Replace fake responses with real API calls.
   - Connect `sheetContext` inputs to the request body.
   - Render tool outputs using refactored feature subcomponents.

6. **Cleanup & UX Polish**
   - Remove or hide old tab-based navigation in `app/page.tsx`.
   - Keep `/api/sheets/*` routes for compatibility (or deprecate later).
   - Improve loading states, error messages, and empty-state copy.

7. **Optional Enhancements**
   - Streaming responses using `LLMClient.chatStream` and a streaming route.
   - Supabase persistence and session sidebar.
   - Basic analytics (e.g., issues detected per session, tool usage).

---

## 9. Risks and Considerations

- **LLM JSON Robustness**
  - The agent prompt must strongly enforce strict JSON-only responses.
  - Add defensive parsing and fallback error messages when parsing fails.

- **Tool Safety**
  - `SheetModifier` should keep `allowDestructive: false` by default.
  - For destructive actions, require explicit user confirmation in chat.

- **Latency**
  - Tool calls (especially with LLM and Sheets API) may be slow.
  - Use clear loading indicators and concise assistant messages while waiting.

- **Auth & Permissions**
  - Ensure service account access and error paths are clearly surfaced in chat when Sheets access fails.

---

## 10. Definition of Done (Phase 1)

- User can:
  - Open the app and see a single chat interface.
  - Configure a spreadsheet and sheet title in the UI.
  - Ask the agent to “check this sheet for issues” and see a rich issues card in the chat.
  - Ask the agent to “add a Total column” and see a modification plan + result summary in the chat.
  - Ask the agent to “create a new sheet for X” and receive a new sheet link + plan in the chat.
- All flows work without any external DB; sessions are transient (or stored only in local state/localStorage).


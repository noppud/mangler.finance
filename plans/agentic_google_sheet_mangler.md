# Plan: Agentic Google Sheet Mangler

Goal: Build an “agentic” system that can (1) detect mistakes in existing Google Sheets, (2) modify existing sheets based on natural language prompts, and (3) create new sheets from prompts.

## Stage 0 – Product Definition
- Define primary user personas (analysts, operators, finance teams, general knowledge workers).
- Enumerate core use cases for each of the three capabilities (spot mistakes, modify sheets, create sheets).
- Decide initial surface: standalone web app, Chrome extension, or Google Workspace Add-on.
- Define guardrails: what the agent is allowed to change, and how users confirm changes.

## Stage 1 – Google Sheets Integration
- Set up Google Cloud project, OAuth consent screen, and credentials.
- Implement authentication and authorization (OAuth 2.0) for user access to their Sheets.
- Wrap Google Sheets API in a thin service layer (read ranges, write ranges, add/delete sheets, formatting).
- Add support for reading sheet metadata (names, dimensions, data validation, formulas).

## Stage 2 – Data Representation & Context Builder
- Define internal representation for sheets (cells, ranges, formulas, types, inferred schemas).
- Implement a context builder that:
  - Samples and summarizes large sheets (stats, distributions, headers, anomalies).
  - Detects table regions, header rows, and data types automatically.
  - Generates compact textual/JSON descriptions suitable as LLM input.

## Stage 3 – Mistake Detection Engine
- Catalog error types: formula errors, inconsistent formulas, type mismatches, outliers, missing values, broken references, duplicate keys, constraint violations, etc.
- Implement rule-based checks that run without LLM (fast, deterministic).
- Implement LLM-based analysis for higher-level issues (semantic anomalies, logical inconsistencies, suspicious patterns).
- Combine rule-based and LLM findings into a unified “issues” model with severity, location, and explanation.
- Design configuration for which checks to run and thresholds for flagging.

## Stage 4 – Prompt-Based Modification Engine
- Design prompt schema for “modify existing sheet”:
  - User instruction (natural language).
  - Sheet context (schema, samples, inferred intents).
  - Safety constraints (max affected rows/columns, protected ranges).
- Implement an LLM planner that:
  - Interprets user intent.
  - Produces a sequence of concrete edit actions (add column, update formulas, normalize data, reformat, etc.).
  - Estimates impact (rows/columns touched).
- Implement an executor that:
  - Simulates actions on an in-memory copy first.
  - Validates no obvious data loss or corruption.
  - Applies actions to the live sheet via the Sheets API.
- Add dry-run mode and human confirmation previews before applying large changes.

## Stage 5 – Prompt-Based Sheet Creation
- Design prompt schema for “create new sheet”:
  - User intent (e.g. “sales pipeline tracker for small SaaS”).
  - Optional constraints (number of sheets, columns, integrations).
- Implement LLM templates that:
  - Propose sheet structure (tabs, columns, data types, formulas, validation rules).
  - Generate example rows and documentation notes in a separate “Readme” tab.
- Implement a generator that:
  - Translates LLM output into concrete Sheets API calls (create spreadsheet, tabs, formats, validation).
  - Applies naming conventions and safe defaults (frozen header rows, clear date/number formats).

## Stage 6 – Agent Orchestration & Memory
- Implement an agent loop that:
  - Reads current sheet state and user prompt.
  - Chooses between “detect issues”, “modify”, or “create” workflows (or combinations).
  - Breaks complex tasks into sub-steps (analyze → propose plan → apply edits → verify).
- Add short-term memory for the current session (decisions taken, issues found, user approvals).
- Optionally add long-term memory for a given spreadsheet (past fixes, known patterns, user preferences).

## Stage 7 – UI / UX
- Build a minimal UI (web app or add-on) with:
  - Sheet picker (list of accessible spreadsheets).
  - Prompt box and history of interactions.
  - Issues panel showing detected problems, locations, and suggested fixes.
  - Change preview diff (before/after for affected ranges) with approval controls.
- Add clear affordances for:
  - “Scan this sheet for mistakes”.
  - “Apply this instruction to this sheet”.
  - “Create a new sheet from this prompt”.
- Include safety indicators and undo options (e.g. store backups, suggest using version history).

## Stage 8 – Evaluation, Logging & Safety
- Log all agent actions, prompts, and applied changes (with cell-level diffs) for audit and debugging.
- Define evaluation datasets (synthetic and real sheets) to benchmark:
  - Mistake detection recall/precision.
  - Task success rate for modification and creation tasks.
  - User satisfaction and edit acceptance rate.
- Implement rate limiting and cost controls around LLM usage.
- Add safeguards to avoid accidental data exposure in prompts (mask PII where possible).

## Stage 9 – Deployment & Iteration
- Package backend (API + agents) and frontend for staging and production.
- Run a private beta with selected users; collect feedback on UX and reliability.
- Iterate on:
  - Common mistake patterns to add more rules.
  - Prompt templates and planner logic for complex edits.
  - Default sheet templates for popular use cases.
- Plan future extensions (support for Excel, CSV, BigQuery-connected sheets, etc.).


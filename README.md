# Sheet Mangler

An AI-powered Google Sheets assistant that can detect mistakes, modify existing sheets, and create new spreadsheets from natural language prompts.

## Features

### 1. Mistake Detection
- **Rule-based checks**: Formula errors, type mismatches, missing values, duplicates
- **LLM-based analysis**: Semantic anomalies, logical inconsistencies, suspicious patterns
- Severity classification and suggested fixes

### 2. Sheet Modification
- Describe what you want to change in natural language
- AI generates and executes a plan of actions
- Supports: adding/removing columns, updating formulas, normalizing data, and more
- Safety constraints to prevent accidental data loss

### 3. Sheet Creation
- Describe your spreadsheet needs in plain English
- AI designs the structure with appropriate columns, data types, and validation
- Auto-generates example data and documentation
- Creates formatted, ready-to-use spreadsheets

## Setup

### Prerequisites
- Node.js 18+ and npm/yarn/pnpm
- Google Cloud Project with Sheets API enabled
- OpenRouter API key

### 1. Install Dependencies

First, fix npm cache permissions (if needed):
```bash
sudo chown -R $(whoami) ~/.npm
```

Then install dependencies:
```bash
npm install
# or
yarn install
# or
pnpm install
```

### 2. Set Up Google Cloud Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API" and enable it
   - Also enable "Google Drive API" for file listing
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: "Web application"
   - Authorized redirect URIs: `http://localhost:3000/api/auth/callback/google`
   - Copy the Client ID and Client Secret

### 3. Get OpenRouter API Key

1. Go to [OpenRouter](https://openrouter.ai/)
2. Sign up and create an API key
3. Add credits to your account

### 4. Configure Environment Variables

Copy the example environment file:
```bash
cp .env.local.example .env.local
```

Edit `.env.local` and fill in your credentials:
```env
# Google Cloud OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# OpenRouter API
OPENROUTER_API_KEY=your_openrouter_api_key

# NextAuth
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your_nextauth_secret_here  # Generate with: openssl rand -base64 32

# Default model for OpenRouter (can be changed)
DEFAULT_LLM_MODEL=anthropic/claude-3.5-sonnet
```

### 5. Run the Development Server

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Usage

### Detecting Mistakes

1. Sign in with your Google account
2. Go to the "Detect Mistakes" tab
3. Enter the Spreadsheet ID (from the URL: `docs.google.com/spreadsheets/d/SPREADSHEET_ID/...`)
4. Enter the sheet name (e.g., "Sheet1")
5. Click "Detect Issues"

### Modifying Sheets

1. Go to the "Modify Sheet" tab
2. Enter the Spreadsheet ID and sheet name
3. Describe what you want to change in natural language:
   - "Add a column called 'Total' that sums columns B and C"
   - "Sort the data by the 'Date' column in descending order"
   - "Convert all email addresses in column D to lowercase"
4. Click "Modify Sheet"
5. Review the plan and changes

### Creating New Sheets

1. Go to the "Create Sheet" tab
2. Describe your spreadsheet:
   - "Create a project management tracker with tasks, deadlines, assignees, and status"
   - "Build an expense tracker for a small business with categories and monthly summaries"
   - "Make a customer database with contact information and purchase history"
3. Click "Create Sheet"
4. Click the link to open your new spreadsheet

## Architecture

### Backend (Next.js API Routes)
- `/api/auth/[...nextauth]` - NextAuth authentication
- `/api/sheets/detect` - Mistake detection endpoint
- `/api/sheets/modify` - Sheet modification endpoint
- `/api/sheets/create` - Sheet creation endpoint

### Core Services
- **SheetsClient** (`lib/sheets/client.ts`) - Google Sheets API wrapper
- **ContextBuilder** (`lib/sheets/context-builder.ts`) - Analyzes and summarizes sheet data
- **LLMClient** (`lib/llm/client.ts`) - OpenRouter integration
- **MistakeDetector** (`lib/agents/mistake-detector.ts`) - Error detection engine
- **SheetModifier** (`lib/agents/modifier.ts`) - Sheet modification agent
- **SheetCreator** (`lib/agents/creator.ts`) - Sheet creation agent

### Frontend (React Components)
- `components/features/DetectIssues.tsx` - Mistake detection UI
- `components/features/ModifySheet.tsx` - Sheet modification UI
- `components/features/CreateSheet.tsx` - Sheet creation UI
- `components/ui/*` - Reusable UI components

## Security & Safety

- All operations require Google OAuth authentication
- Sheet modifications have safety constraints (max rows/columns affected)
- Destructive actions require explicit permission
- All actions are logged for audit trails
- Uses NEXTAUTH_SECRET for session security

## Development

### Type Definitions
All types are defined in `types/`:
- `sheets.ts` - Sheet data structures
- `errors.ts` - Error/issue definitions
- `agents.ts` - Agent action types
- `llm.ts` - LLM integration types

### Adding New Features

To add a new type of sheet operation:
1. Define action types in `types/agents.ts`
2. Add LLM prompt in `lib/llm/prompts.ts`
3. Implement logic in appropriate agent (`lib/agents/`)
4. Create API route in `app/api/sheets/`
5. Build UI component in `components/features/`

## License

ISC

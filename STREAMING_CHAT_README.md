# Sheet Mangler Chat with Streaming Support

## Overview

The Sheet Mangler chat interface has been updated with streaming support for real-time responses, providing a better user experience similar to modern AI chat applications.

## Features

### 1. **Streaming Chat Endpoints**
- `/chat` - Standard endpoint (returns complete response)
- `/chat/stream` - New SSE (Server-Sent Events) streaming endpoint
- Real-time token streaming for assistant responses
- Progressive rendering of content as it's generated

### 2. **Multiple Chat Interfaces**

#### SvelteKit Web App (`/chat`)
- Full-featured chat interface at `https://mangler.finance/chat`
- Dark theme consistent with Mangler branding
- Real-time streaming responses
- Issue detection and visualization
- Fix suggestions with one-click application
- Session persistence for conversation context

#### Google Sheets Sidebar
- Two versions available:
  - `Sidebar.html` - Original implementation using Google Apps Script calls
  - `SidebarStreaming.html` - New version with streaming support
- Automatically gets spreadsheet context
- Inline issue cards with fix/ignore actions
- Seamless integration with Google Sheets

#### Embeddable Widget
- Standalone HTML widget served at `/widget`
- Can be embedded in any webpage or iframe
- Automatically detects Google Sheets context when embedded
- Responsive design that works in various container sizes

### 3. **Streaming Protocol**

The streaming endpoint uses Server-Sent Events (SSE) with the following message types:

```javascript
// Session initialization
{ type: 'session', sessionId: 'session_xxx' }

// Content streaming
{ type: 'content', role: 'assistant', content: 'word ', messageId: 'msg_xxx' }

// Tool responses (issues detected)
{ type: 'tool', metadata: { payload: { potential_errors: [...] } } }

// Completion signal
{ type: 'done' }

// Error handling
{ type: 'error', error: 'Error message' }
```

### 4. **Issue Detection & Fixes**

Issues are displayed with:
- Cell location
- Severity level (low/medium/high/critical)
- Color coding
- Description
- Suggested fixes
- One-click fix application
- Ignore option

## API Endpoints

### Python Backend (FastAPI)

```
POST /chat          - Standard chat endpoint
POST /chat/stream   - Streaming chat endpoint (SSE)
GET  /widget        - Serves embeddable widget HTML
POST /tools/color   - Apply color highlights to cells
POST /tools/restore - Restore original cell colors
```

## Usage

### In SvelteKit App

Navigate to `/chat` in the Mangler web application to access the full chat interface.

### In Google Sheets

1. Open your Google Sheet
2. Go to Extensions → Apps Script
3. Replace the sidebar HTML with `SidebarStreaming.html`
4. Use the menu to open the Mangler sidebar

### As Embedded Widget

```html
<iframe
  src="https://fintech-hackathon-production.up.railway.app/widget?sheet=SHEET_URL&title=Sheet1"
  width="400"
  height="600">
</iframe>
```

## Configuration

### CORS Settings

The backend automatically allows:
- `http://localhost:5173` (dev)
- `https://mangler.finance`
- `https://www.mangler.finance`
- Additional origins via `CORS_ALLOWED_ORIGINS` environment variable

### Environment Variables

```bash
# API Configuration
DEFAULT_SPREADSHEET_URL=https://docs.google.com/spreadsheets/d/xxx
GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/credentials.json

# CORS (optional)
CORS_ALLOWED_ORIGINS=https://custom-domain.com,https://another-domain.com
```

## Implementation Details

### Streaming Simulation

Currently, the streaming implementation simulates real-time token generation by:
1. Getting the complete response from the LLM
2. Breaking it into words
3. Streaming each word with a small delay

In production, this should be replaced with actual token streaming from the LLM API.

### Session Management

- Sessions are automatically created and persisted
- Each interface maintains its own session
- Sessions include conversation history for context
- Session IDs follow the pattern: `session_{source}_{timestamp}_{random}`

### Error Handling

- Graceful degradation when streaming fails
- Automatic reconnection attempts
- Clear error messages to users
- Fallback to non-streaming mode if needed

## Future Enhancements

1. **True LLM Streaming**: Integrate with OpenAI/Anthropic streaming APIs
2. **WebSocket Support**: Alternative to SSE for bidirectional communication
3. **File Upload**: Support for analyzing uploaded spreadsheets
4. **Collaborative Features**: Multiple users in same session
5. **Voice Input**: Speech-to-text for queries
6. **Export Chat History**: Save conversations as PDF/Markdown
7. **Custom Themes**: User-selectable color schemes
8. **Keyboard Shortcuts**: Power user features

## Testing

Test the streaming functionality:

1. **Local Development**:
   ```bash
   # Backend
   cd python_backend
   uvicorn api:app --reload

   # Frontend
   cd mangler-ui
   npm run dev
   ```

2. **Production**:
   - Visit https://mangler.finance/chat
   - Or https://fintech-hackathon-production.up.railway.app/widget

3. **Google Sheets**:
   - Install the Apps Script
   - Open sidebar from menu
   - Test with a sample spreadsheet

## Troubleshooting

### Streaming Not Working
- Check CORS settings
- Verify SSL certificates (SSE requires HTTPS in production)
- Check for proxy/CDN buffering (Nginx, Cloudflare)
- Ensure `X-Accel-Buffering: no` header is set

### Session Issues
- Clear browser cache
- Check session timeout settings
- Verify backend session storage

### Google Sheets Integration
- Ensure Apps Script has necessary permissions
- Check for Content Security Policy issues
- Verify API endpoint accessibility
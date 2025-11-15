# Tools API Guide

This guide documents the new tool endpoints added to the FastAPI backend in `python_backend/api.py`.

## Overview

Three new endpoints have been added to enable spreadsheet color management:

1. **`POST /tools/color`** - Apply background colors to cells
2. **`POST /tools/snapshot`** - Snapshot cell colors to Supabase
3. **`POST /tools/restore`** - Restore cell colors from Supabase snapshot

## Prerequisites

- FastAPI server running (`python -m uvicorn python_backend.api:app`)
- Google Sheets API credentials configured
- Supabase URL and service key in `.env` (for snapshot/restore)
- Environment variables:
  - `SPREADSHEET_URL`: Target Google Sheet URL
  - `SUPABASE_URL`: Supabase project URL
  - `SUPABASE_SERVICE_KEY`: Supabase service key

---

## Endpoint 1: Apply Colors

### `POST /tools/color`

Apply background colors to cells in your spreadsheet.

**Request Body:**
```json
[
  {
    "cell_location": "A1",
    "message": "Error in formula",
    "color": "#FF0000"
  },
  {
    "cell_location": "B2:C5",
    "message": "Warning: May contain errors",
    "color": "#FFFF00"
  }
]
```

**Parameters:**
- `cell_location` (string): Single cell (e.g., "A1") or range (e.g., "B2:C5")
- `message` (string): Note/comment to add to the cell(s)
- `color` (string): Hex color code (with or without #)

**Response (Success - 200):**
```json
{
  "status": "success",
  "message": "Colored 2 range(s) on 'Sheet1'.",
  "count": 2
}
```

**Response (Error - 400):**
```json
{
  "detail": "Invalid hex color '#GGGGGG'."
}
```

**Example cURL:**
```bash
curl -X POST http://localhost:8000/tools/color \
  -H "Content-Type: application/json" \
  -d '[
    {"cell_location": "A1", "message": "Error", "color": "#FF0000"},
    {"cell_location": "B3:B5", "message": "Warning", "color": "#FFFF00"}
  ]'
```

---

## Endpoint 2: Snapshot Colors

### `POST /tools/snapshot`

Take a snapshot of current cell colors and store in Supabase for later restoration.

**Request Body:**
```json
{
  "cell_locations": ["A1", "B2:C5", "D10"]
}
```

**Parameters:**
- `cell_locations` (array): List of cells or ranges to snapshot

**Response (Success - 200):**
```json
{
  "status": "success",
  "message": "Stored 10 cell color(s) across 3 batch id(s).",
  "snapshot_batch_id": "123e4567-e89b-12d3-a456-426614174000",
  "total_cells": 10,
  "total_batches": 3
}
```

**Response (Error - 400):**
```json
{
  "detail": "No sheets available in spreadsheet."
}
```

**Example cURL:**
```bash
curl -X POST http://localhost:8000/tools/snapshot \
  -H "Content-Type: application/json" \
  -d '{"cell_locations": ["A1:D10", "F5:G8"]}'
```

**Important:** Save the `snapshot_batch_id` - you'll need it to restore colors later!

---

## Endpoint 3: Restore Colors

### `POST /tools/restore`

Restore cell colors from a previously saved snapshot.

**Request Body:**
```json
{
  "snapshot_batch_id": "123e4567-e89b-12d3-a456-426614174000",
  "cell_locations": ["A1", "B2:C5"]
}
```

**Parameters:**
- `snapshot_batch_id` (string, required): The batch ID from the snapshot endpoint
- `cell_locations` (array, optional): Specific cells to restore (if not provided, all snapshot cells are restored)

**Response (Success - 200):**
```json
{
  "status": "success",
  "message": "Restored 10 cell color(s) on 'Sheet1' from snapshot batch.",
  "count": 10
}
```

**Response (Error - 400):**
```json
{
  "detail": "No snapshot rows found for batch id '123e4567-e89b-12d3-a456-426614174000'."
}
```

**Example cURL:**
```bash
curl -X POST http://localhost:8000/tools/restore \
  -H "Content-Type: application/json" \
  -d '{
    "snapshot_batch_id": "123e4567-e89b-12d3-a456-426614174000",
    "cell_locations": ["A1:D10"]
  }'
```

---

## Common Use Cases

### Use Case 1: Color cells with potential errors

```bash
# Apply red color to error cells
curl -X POST http://localhost:8000/tools/color \
  -H "Content-Type: application/json" \
  -d '[
    {"cell_location": "A1", "message": "Formula error", "color": "#FF0000"},
    {"cell_location": "C5:C10", "message": "Circular reference", "color": "#FF3333"}
  ]'
```

### Use Case 2: Save and restore workflow

```bash
# Step 1: Snapshot current state
BATCH_ID=$(curl -s -X POST http://localhost:8000/tools/snapshot \
  -H "Content-Type: application/json" \
  -d '{"cell_locations": ["A1:Z100"]}' | jq -r '.snapshot_batch_id')

echo "Saved snapshot: $BATCH_ID"

# Step 2: Apply some colors
curl -X POST http://localhost:8000/tools/color \
  -H "Content-Type: application/json" \
  -d '[{"cell_location": "A1:Z100", "message": "Test", "color": "#FFFF00"}]'

# Step 3: Restore original colors later
curl -X POST http://localhost:8000/tools/restore \
  -H "Content-Type: application/json" \
  -d "{\"snapshot_batch_id\": \"$BATCH_ID\"}"
```

---

## Supported Color Formats

All endpoints accept hex colors in the following formats:
- `#FF0000` (with hash)
- `FF0000` (without hash)

RGB values are automatically converted to the 0-1 range required by Google Sheets API.

### Common Colors:
- Red (error): `#FF0000`
- Orange (warning): `#FFA500`
- Yellow (info): `#FFFF00`
- Green (success): `#00FF00`
- Blue (info): `#0000FF`
- Gray (neutral): `#808080`

---

## Error Handling

All errors return HTTP 400 with a detail message explaining what went wrong:

| Error | Cause |
|-------|-------|
| Invalid hex color | Color format not recognized (use #RRGGBB) |
| Invalid cell reference | Cell reference doesn't match pattern (e.g., "A1") |
| Range has inverted bounds | End cell is before start cell (e.g., "Z1:A1") |
| No sheets available | Spreadsheet has no sheets |
| SUPABASE_URL not configured | Missing Supabase environment variables |
| No snapshot rows found | Batch ID doesn't exist in Supabase |

---

## Implementation Details

### Cell Reference Format
- **Single cell:** `A1`, `Z10`, `AA20`
- **Range:** `A1:D10`, `B2:C5`

### Color Snapshot Storage
- Colors are stored in Supabase table: `cell_color_snapshots`
- Each snapshot batch has a deterministic UUID based on: `spreadsheet_id:gid:range`
- Enables reproducible snapshots - same inputs always produce same batch ID

### Excel/Sheets API Compatibility
- Ranges use inclusive lower bounds and exclusive upper bounds internally
- Row and column indices are 0-based internally, 1-based in cell references
- Handles both single cells and multi-cell ranges transparently

---

## Testing

### Quick Test (with Python)

```python
import requests
import json

BASE_URL = "http://localhost:8000"

# Test color endpoint
response = requests.post(
    f"{BASE_URL}/tools/color",
    json=[
        {"cell_location": "A1", "message": "Test", "color": "#FF0000"}
    ]
)
print("Color response:", response.json())

# Test snapshot
response = requests.post(
    f"{BASE_URL}/tools/snapshot",
    json={"cell_locations": ["A1:D10"]}
)
result = response.json()
print("Snapshot response:", result)
batch_id = result.get("snapshot_batch_id")

# Test restore
if batch_id:
    response = requests.post(
        f"{BASE_URL}/tools/restore",
        json={"snapshot_batch_id": batch_id}
    )
    print("Restore response:", response.json())
```

---

## Integration with Chat API

These endpoints are designed to work alongside the existing `/chat` endpoint. Your LLM can:

1. Analyze formulas using the chat endpoint
2. Use `/tools/color` to highlight problematic cells
3. Use `/tools/snapshot` before making changes
4. Use `/tools/restore` to undo if needed

---

## Troubleshooting

**Q: Getting "No sheets available" error**
- A: Ensure your `SPREADSHEET_URL` environment variable is correct and points to a valid Google Sheet

**Q: Snapshot returns success but restore fails with "No snapshot rows found"**
- A: Supabase credentials may be incorrect or database not initialized. Check `.env` for `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`

**Q: Colors aren't being applied**
- A: Check that credentials have write access to the spreadsheet and Google Sheets API is enabled

**Q: Getting authentication errors**
- A: Ensure `client_secret_*.json` file exists and `token.json` is properly generated from OAuth flow

---

## Future Enhancements

Potential improvements:
- Batch operations optimization
- Cell style endpoints (font, borders, alignment)
- Conditional formatting rules
- Color palette presets
- Snapshot history and comparison


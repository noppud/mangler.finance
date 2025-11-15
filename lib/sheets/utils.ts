// Small helpers for working with Google Sheets identifiers.

/**
 * Normalize a "spreadsheet ID" value that may actually be a full URL.
 *
 * Accepts either:
 * - the raw spreadsheet ID: `1ABC...XYZ`
 * - a full Sheets URL: `https://docs.google.com/spreadsheets/d/1ABC...XYZ/edit#gid=0`
 *
 * In both cases this returns the bare ID string that the Google Sheets API expects.
 */
export function normalizeSpreadsheetId(raw: string): string {
  if (!raw) return raw;

  const trimmed = raw.trim();

  // Try to extract ID from a full URL
  const match = trimmed.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/);
  if (match && match[1]) {
    return match[1];
  }

  // Assume caller passed the bare ID already
  return trimmed;
}


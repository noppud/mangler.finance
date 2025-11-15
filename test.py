"""
Google Sheets Formula Validator
Analyzes Google Sheets documents for formula logic errors.
* Extracts all formulas from a sheet
* Detects common formula issues
"""

import os
import json
import re
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as UserCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass

# * Load environment variables from .env
load_dotenv()

Color = Dict[str, float]


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# * Default configuration (loaded from .env, no fallbacks)
DEFAULT_SPREADSHEET_URL = os.environ["SPREADSHEET_URL"]
DEFAULT_CREDENTIALS_PATH = os.environ["CREDENTIALS_PATH"]
OAUTH_PORT = int(os.getenv("OAUTH_PORT") or os.environ["OAUTH_PORT"])
FORMULA_CELL_COLOR: Color = {
    "red": float(os.environ["FORMULA_CELL_RED"]),
    "green": float(os.environ["FORMULA_CELL_GREEN"]),
    "blue": float(os.environ["FORMULA_CELL_BLUE"])
}
INTEGER_CELL_COLOR: Color = {
    "red": float(os.environ["INTEGER_CELL_RED"]),
    "green": float(os.environ["INTEGER_CELL_GREEN"]),
    "blue": float(os.environ["INTEGER_CELL_BLUE"])
}


@dataclass
class FormulaIssue:
    """# * Represents a potential formula issue"""
    cell: str
    formula: str
    issue_type: str
    severity: str  # "error", "warning", "info"
    message: str
    suggestions: List[str]


class GoogleSheetsFormulaValidator:
    """# * Main validator for Google Sheets formulas"""

    def __init__(self, credentials_path: str = "credentials.json"):
        """
        Initialize the validator with Google Sheets API credentials.
        
        # TODO: Support both service account and OAuth flows
        """
        self.service = None
        self.spreadsheet_id = None
        self.credentials_path = credentials_path
        self._authenticate()

    def _authenticate(self) -> None:
        """# * Authenticate with Google Sheets API"""
        creds = None

        # Check for existing token
        if os.path.exists("token.json"):
            creds = UserCredentials.from_authorized_user_file("token.json", SCOPES)
        
        # If no valid credentials, run OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=OAUTH_PORT)
            
            # Save credentials for future use
            with open("token.json", "w") as token:
                token.write(creds.to_json())

        self.service = build("sheets", "v4", credentials=creds)

    def get_spreadsheet(self, spreadsheet_id: str) -> Dict[str, Any]:
        """# * Fetch spreadsheet metadata"""
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            return spreadsheet
        except HttpError as error:
            raise Exception(f"API Error: {error}")

    def get_sheet_title_by_gid(self, spreadsheet_id: str, gid: int) -> str:
        """# * Resolve sheet title by gid (sheetId)"""
        spreadsheet = self.get_spreadsheet(spreadsheet_id)
        for sheet in spreadsheet.get("sheets", []):
            props = sheet.get("properties", {})
            if props.get("sheetId") == gid:
                return props.get("title")
        raise Exception(f"No sheet found with gid={gid}")

    def get_sheet_properties(self, spreadsheet_id: str, sheet_name: str) -> Dict[str, Any]:
        """# * Get sheet properties by name"""
        spreadsheet = self.get_spreadsheet(spreadsheet_id)
        for sheet in spreadsheet.get("sheets", []):
            props = sheet.get("properties", {})
            if props.get("title") == sheet_name:
                return props
        raise Exception(f"Sheet '{sheet_name}' not found in spreadsheet")

    def get_all_formulas(self, spreadsheet_id: str, sheet_name: str = None) -> Dict[str, str]:
        """
        # * Extract all formulas from a sheet
        # ? Returns dict mapping cell address to formula
        """
        try:
            spreadsheet = self.get_spreadsheet(spreadsheet_id)
            
            sheets = spreadsheet.get("sheets", [])
            if not sheets:
                raise Exception("No sheets found in spreadsheet")

            # Use first sheet if not specified
            if sheet_name is None:
                sheet_name = sheets[0]["properties"]["title"]

            # Get all data including formulas
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_name}'!A:Z",
                valueRenderOption="FORMULA"
            ).execute()

            values = result.get("values", [])
            formulas = {}

            for row_idx, row in enumerate(values, start=1):
                for col_idx, cell_value in enumerate(row, start=1):
                    if isinstance(cell_value, str) and cell_value.startswith("="):
                        cell_address = self._get_cell_address(row_idx, col_idx)
                        formulas[cell_address] = cell_value

            return formulas

        except HttpError as error:
            raise Exception(f"API Error: {error}")

    def get_sheet_values(self, spreadsheet_id: str, sheet_name: str, value_render_option: str) -> List[List[Any]]:
        """# * Fetch sheet values with specified render option"""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_name}'",
                valueRenderOption=value_render_option,
                majorDimension="ROWS"
            ).execute()
            return result.get("values", [])
        except HttpError as error:
            raise Exception(f"API Error: {error}")

    def analyze_formulas(self, formulas: Dict[str, str]) -> List[FormulaIssue]:
        """# * Analyze formulas for potential logic errors"""
        issues = []

        for cell, formula in formulas.items():
            cell_issues = self._check_formula(cell, formula)
            issues.extend(cell_issues)

        return issues

    def _check_formula(self, cell: str, formula: str) -> List[FormulaIssue]:
        """# * Run all checks on a single formula"""
        issues = []

        # Run individual checks
        issues.extend(self._check_circular_references(cell, formula))
        issues.extend(self._check_missing_functions(cell, formula))
        issues.extend(self._check_unmatched_parentheses(cell, formula))
        issues.extend(self._check_empty_ranges(cell, formula))
        issues.extend(self._check_common_mistakes(cell, formula))

        return issues

    def _check_circular_references(self, cell: str, formula: str) -> List[FormulaIssue]:
        """# ! Detect potential circular reference patterns"""
        issues = []
        
        # Simple heuristic: check if formula references its own cell
        cell_ref = self._extract_cell_from_address(cell)
        if cell_ref in formula.upper():
            issues.append(FormulaIssue(
                cell=cell,
                formula=formula,
                issue_type="circular_reference",
                severity="error",
                message=f"Formula may reference its own cell: {cell}",
                suggestions=[
                    "Review formula to ensure it doesn't create a circular dependency",
                    f"Check if {cell} should reference a different cell"
                ]
            ))
        
        return issues

    def _check_missing_functions(self, cell: str, formula: str) -> List[FormulaIssue]:
        """# * Detect potentially misspelled or invalid functions"""
        issues = []
        
        # Extract function names (word followed by parenthesis)
        functions = re.findall(r'\b([A-Z_]+)\s*\(', formula.upper())
        
        # Common Google Sheets functions
        valid_functions = {
            'SUM', 'AVERAGE', 'COUNT', 'MAX', 'MIN', 'IF', 'VLOOKUP', 'HLOOKUP',
            'INDEX', 'MATCH', 'INDIRECT', 'CONCATENATE', 'TRIM', 'UPPER', 'LOWER',
            'LEN', 'FIND', 'SUBSTITUTE', 'IFERROR', 'ISNA', 'ISBLANK', 'AND', 'OR',
            'NOT', 'SUMIF', 'COUNTIF', 'AVERAGEIF', 'DATE', 'TODAY', 'NOW', 'YEAR',
            'MONTH', 'DAY', 'HOUR', 'MINUTE', 'SECOND', 'ROWS', 'COLUMNS', 'TRANSPOSE',
            'SORT', 'FILTER', 'UNIQUE', 'FLATTEN', 'QUERY', 'ARRAYFORMULA', 'SUMPRODUCT',
            'PRODUCT', 'POWER', 'SQRT', 'ABS', 'ROUND', 'ROUNDUP', 'ROUNDDOWN', 'MOD',
            'QUOTIENT', 'RAND', 'RANDBETWEEN', 'TEXT', 'VALUE', 'SPLIT', 'JOIN',
            'REGEXMATCH', 'REGEXEXTRACT', 'REGEXREPLACE', 'TO_DATE', 'TO_PERCENT',
            'TO_TEXT', 'TO_DOLLARS', 'SPARKLINE', 'IMAGE', 'HYPERLINK', 'IMPORTRANGE',
            'IMPORTHTML', 'IMPORTFEED', 'GOOGLETRANSLATE', 'GOOGLE_TRANSLATE'
        }
        
        for func in functions:
            if func not in valid_functions:
                issues.append(FormulaIssue(
                    cell=cell,
                    formula=formula,
                    issue_type="unknown_function",
                    severity="warning",
                    message=f"Unknown or misspelled function: {func}",
                    suggestions=[
                        f"Verify that '{func}' is a valid Google Sheets function",
                        "Check for typos in function name",
                        "Refer to Google Sheets function list for alternatives"
                    ]
                ))
        
        return issues

    def _check_unmatched_parentheses(self, cell: str, formula: str) -> List[FormulaIssue]:
        """# * Detect unmatched parentheses"""
        issues = []
        
        # Remove string contents to avoid false positives
        formula_stripped = re.sub(r'"[^"]*"', '""', formula)
        
        open_count = formula_stripped.count('(')
        close_count = formula_stripped.count(')')
        
        if open_count != close_count:
            issues.append(FormulaIssue(
                cell=cell,
                formula=formula,
                issue_type="unmatched_parentheses",
                severity="error",
                message=f"Unmatched parentheses: {open_count} open, {close_count} close",
                suggestions=[
                    "Review formula syntax",
                    f"Expected equal number of opening and closing parentheses"
                ]
            ))
        
        return issues

    def _check_empty_ranges(self, cell: str, formula: str) -> List[FormulaIssue]:
        """# * Detect suspicious empty range patterns"""
        issues = []
        
        # Look for patterns like SUM(), COUNT(), etc. with no arguments
        empty_func_pattern = r'\b([A-Z_]+)\s*\(\s*\)'
        matches = re.findall(empty_func_pattern, formula.upper())
        
        if matches:
            for func in matches:
                issues.append(FormulaIssue(
                    cell=cell,
                    formula=formula,
                    issue_type="empty_function_call",
                    severity="warning",
                    message=f"Function called with no arguments: {func}()",
                    suggestions=[
                        f"Add range or parameters to {func}()",
                        "Example: SUM(A:A) or COUNT(B1:B100)"
                    ]
                ))
        
        return issues

    def _check_common_mistakes(self, cell: str, formula: str) -> List[FormulaIssue]:
        """# * Detect common formula mistakes"""
        issues = []
        
        # Check for space in range reference (common mistake)
        if re.search(r'[A-Z]\d+\s*:\s*[A-Z]\d+', formula):
            pass  # This is actually valid, spaces around : are OK
        
        # Check for comma instead of semicolon in some contexts
        # ! Note: Google Sheets uses commas or semicolons depending on locale
        
        # Check for division by zero patterns (hard to detect but flag suspicious patterns)
        if re.search(r'/\s*(0|"0")', formula):
            issues.append(FormulaIssue(
                cell=cell,
                formula=formula,
                issue_type="division_by_zero",
                severity="warning",
                message="Formula contains division by zero",
                suggestions=[
                    "Use IFERROR to handle division by zero",
                    "Example: =IFERROR(A1/B1, 0)"
                ]
            ))
        
        # Check for IF with missing argument
        if_pattern = r'IF\s*\(\s*[^,]+\s*,\s*\)'
        if re.search(if_pattern, formula.upper()):
            issues.append(FormulaIssue(
                cell=cell,
                formula=formula,
                issue_type="incomplete_if",
                severity="error",
                message="IF statement missing value arguments",
                suggestions=[
                    "IF requires format: IF(condition, value_if_true, value_if_false)",
                    "Example: =IF(A1>0, 'positive', 'non-positive')"
                ]
            ))
        
        return issues

    @staticmethod
    def _get_cell_address(row: int, col: int) -> str:
        """# * Convert row/col indices to cell address (e.g., A1)"""
        col_label = ""
        while col > 0:
            col -= 1
            col_label = chr(65 + col % 26) + col_label
            col //= 26
        return f"{col_label}{row}"

    @staticmethod
    def _extract_cell_from_address(address: str) -> str:
        """# ? Extract cell reference from address"""
        return re.sub(r'\d+$', '', address)

    def validate_sheet(self, spreadsheet_id: str, sheet_name: str = None) -> Tuple[Dict[str, str], List[FormulaIssue]]:
        """# * Main entry point: validate a sheet"""
        print(f"Fetching formulas from spreadsheet: {spreadsheet_id}")
        formulas = self.get_all_formulas(spreadsheet_id, sheet_name)
        
        print(f"Found {len(formulas)} formulas")
        print("Analyzing formulas...")
        issues = self.analyze_formulas(formulas)
        
        return formulas, issues

    def apply_highlighting(self, spreadsheet_id: str, sheet_name: str) -> None:
        """# * Highlight formula cells (green) and integer value cells (orange)"""
        sheet_props = self.get_sheet_properties(spreadsheet_id, sheet_name)
        sheet_id = sheet_props.get("sheetId")

        formulas_view = self.get_sheet_values(spreadsheet_id, sheet_name, "FORMULA")
        raw_view = self.get_sheet_values(spreadsheet_id, sheet_name, "UNFORMATTED_VALUE")

        max_rows = max(len(formulas_view), len(raw_view))
        max_cols = 0
        for row in formulas_view:
            max_cols = max(max_cols, len(row))
        for row in raw_view:
            max_cols = max(max_cols, len(row))

        if max_rows == 0 or max_cols == 0:
            return

        formula_flags = [[False] * max_cols for _ in range(max_rows)]
        integer_flags = [[False] * max_cols for _ in range(max_rows)]

        for r in range(max_rows):
            formula_row = formulas_view[r] if r < len(formulas_view) else []
            raw_row = raw_view[r] if r < len(raw_view) else []
            for c in range(max_cols):
                formula_value = formula_row[c] if c < len(formula_row) else None
                raw_value = raw_row[c] if c < len(raw_row) else None

                has_formula = isinstance(formula_value, str) and formula_value.startswith("=")
                if has_formula:
                    formula_flags[r][c] = True
                    continue

                if isinstance(raw_value, bool):
                    continue

                if isinstance(raw_value, int):
                    integer_flags[r][c] = True
                    continue

                if isinstance(raw_value, float) and raw_value.is_integer():
                    integer_flags[r][c] = True
                    continue

                if isinstance(raw_value, str):
                    stripped = raw_value.strip()
                    if re.fullmatch(r"-?\d+", stripped):
                        integer_flags[r][c] = True

        requests: List[Dict[str, Any]] = []

        def append_request(row_index: int, start_col: int, end_col: int, color: Color) -> None:
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": row_index,
                        "endRowIndex": row_index + 1,
                        "startColumnIndex": start_col,
                        "endColumnIndex": end_col,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": color
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor"
                }
            })

        for r in range(max_rows):
            c = 0
            while c < max_cols:
                if formula_flags[r][c]:
                    start = c
                    while c < max_cols and formula_flags[r][c]:
                        c += 1
                    append_request(r, start, c, FORMULA_CELL_COLOR)
                    continue

                if integer_flags[r][c]:
                    start = c
                    while c < max_cols and integer_flags[r][c]:
                        c += 1
                    append_request(r, start, c, INTEGER_CELL_COLOR)
                    continue

                c += 1

        if not requests:
            return

        try:
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": requests}
            ).execute()
        except HttpError as error:
            raise Exception(f"API Error: {error}")

    def report_issues(self, issues: List[FormulaIssue]) -> str:
        """# * Generate human-readable issue report"""
        if not issues:
            return "No issues found!"
        
        report = f"Found {len(issues)} potential issues:\n"
        report += "=" * 60 + "\n\n"
        
        by_severity = {"error": [], "warning": [], "info": []}
        for issue in issues:
            by_severity[issue.severity].append(issue)
        
        for severity in ["error", "warning", "info"]:
            if by_severity[severity]:
                report += f"\n{severity.upper()} ({len(by_severity[severity])}):\n"
                report += "-" * 40 + "\n"
                for issue in by_severity[severity]:
                    report += f"\nCell: {issue.cell}\n"
                    report += f"Formula: {issue.formula}\n"
                    report += f"Issue: {issue.message}\n"
                    report += "Suggestions:\n"
                    for suggestion in issue.suggestions:
                        report += f"  - {suggestion}\n"
        
        return report


def main():
    """# * No-arg entrypoint using hardcoded defaults"""
    spreadsheet_url = DEFAULT_SPREADSHEET_URL
    credentials_path = DEFAULT_CREDENTIALS_PATH

    # Extract spreadsheet ID and gid from the hardcoded URL
    url_id_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', spreadsheet_url)
    url_gid_match = re.search(r'[?&]gid=(\d+)', spreadsheet_url)
    spreadsheet_id = url_id_match.group(1) if url_id_match else spreadsheet_url
    if url_id_match:
        spreadsheet_id = url_id_match.group(1)
    gid = int(url_gid_match.group(1)) if url_gid_match else None
    sheet_name = None

    try:
        validator = GoogleSheetsFormulaValidator(credentials_path=credentials_path)
        # Resolve sheet name by gid if provided
        if gid is not None:
            sheet_name = validator.get_sheet_title_by_gid(spreadsheet_id, gid)
        formulas, issues = validator.validate_sheet(spreadsheet_id, sheet_name)
        
        print("\n" + validator.report_issues(issues))

        resolved_sheet_name = sheet_name
        if resolved_sheet_name is None:
            spreadsheet = validator.get_spreadsheet(spreadsheet_id)
            sheets = spreadsheet.get("sheets", [])
            if not sheets:
                raise Exception("No sheets found in spreadsheet")
            resolved_sheet_name = sheets[0]["properties"]["title"]

        print("Applying highlighting for formulas and integers...")
        validator.apply_highlighting(spreadsheet_id, resolved_sheet_name)
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()


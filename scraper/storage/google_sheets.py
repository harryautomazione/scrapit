"""
Google Sheets storage backend for scrapit.

Requires:
- pip install google-api-python-client google-auth-oauthlib

Usage:
1. Set up Google Sheets API credentials:
   - Go to Google Cloud Console
   - Enable Google Sheets API
   - Create OAuth credentials or Service Account
   - Save credentials.json

2. Set environment variables:
   export GOOGLE_SHEETS_CREDENTIALS="/path/to/credentials.json"
   export GOOGLE_SHEETS_SPREADSHEET_ID="your_spreadsheet_id"

   Or provide them at runtime via --sheets-id and --sheets-credentials flags.

3. Run scrapit:
   python -m scraper.main scrape wikipedia --sheets

The scraper will append rows to the specified Google Sheet.
"""

from pathlib import Path
from scraper.config import OUTPUT_DIR

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False

SHEET_NAME = "scrapit_data"


def _get_service(credentials_path: str = None):
    """Initialize Google Sheets API service."""
    import os
    
    if credentials_path is None:
        credentials_path = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
    
    if credentials_path is None:
        raise ValueError(
            "Google Sheets credentials not provided. "
            "Set GOOGLE_SHEETS_CREDENTIALS env var or use --sheets-credentials flag."
        )
    
    creds = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    
    service = build('sheets', 'v4', credentials=creds)
    return service


def _get_spreadsheet_id(spreadsheet_id: str = None):
    """Get spreadsheet ID from env or raise error."""
    import os
    
    if spreadsheet_id is None:
        spreadsheet_id = os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID")
    
    if spreadsheet_id is None:
        raise ValueError(
            "Google Sheets spreadsheet ID not provided. "
            "Set GOOGLE_SHEETS_SPREADSHEET_ID env var or use --sheets-id flag."
        )
    
    return spreadsheet_id


def save(data: dict, name: str, *, spreadsheet_id: str = None, credentials_path: str = None) -> str:
    """
    Save scraped data to Google Sheets.
    
    Args:
        data: Dictionary of field names and values
        name: Directive name (used for logging)
        spreadsheet_id: Google Sheets spreadsheet ID (optional, uses env if not provided)
        credentials_path: Path to Google credentials JSON (optional, uses env if not provided)
    
    Returns:
        Spreadsheet URL
    """
    if not GOOGLE_SHEETS_AVAILABLE:
        raise ImportError(
            "google-api-python-client not installed. "
            "Run: pip install google-api-python-client"
        )
    
    service = _get_service(credentials_path)
    spreadsheet_id = _get_spreadsheet_id(spreadsheet_id)
    
    # Convert data to row values
    row_values = {k: str(v) for k, v in data.items()}
    keys = list(row_values.keys())
    values = [row_values.get(k, "") for k in keys]
    
    try:
        # Try to read existing data to get headers
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{SHEET_NAME}!1:1"
        ).execute()
        
        existing_headers = result.get('values', [[]])[0] if result.get('values') else []
        
        if not existing_headers:
            # No headers yet, write header row first
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{SHEET_NAME}!A1",
                valueInputOption="USER_ENTERED",
                body={"values": [keys]}
            ).execute()
            
            # Write first data row
            service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"{SHEET_NAME}!A2",
                valueInputOption="USER_ENTERED",
                body={"values": [values]}
            ).execute()
        else:
            # Has headers, find new columns and append data
            new_keys = [k for k in keys if k not in existing_headers]
            
            if new_keys:
                # Update header row with new columns
                all_headers = existing_headers + new_keys
                service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f"{SHEET_NAME}!A1",
                    valueInputOption="USER_ENTERED",
                    body={"values": [all_headers]}
                ).execute()
            
            # Get next row
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"{SHEET_NAME}"
            ).execute()
            
            existing_rows = len(result.get('values', []))
            next_row = existing_rows + 1
            
            # Build full row with all columns
            full_row = []
            for header in (existing_headers + new_keys):
                full_row.append(row_values.get(header, ""))
            
            # Append data row
            service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"{SHEET_NAME}!A{next_row}",
                valueInputOption="USER_ENTERED",
                body={"values": [full_row]}
            ).execute()
        
        return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    
    except Exception as e:
        # If sheet doesn't exist, create it
        if "not found" in str(e).lower() or "404" in str(e):
            # Create the sheet
            spreadsheet = {
                'properties': {'title': f'Scrapit - {name}'},
                'sheets': [{'properties': {'title': SHEET_NAME}}]
            }
            spreadsheet = service.spreadsheets().create(
                body=spreadsheet,
                fields='spreadsheetId'
            ).execute()
            
            spreadsheet_id = spreadsheet.get('spreadsheetId')
            
            # Write headers
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{SHEET_NAME}!A1",
                valueInputOption="USER_ENTERED",
                body={"values": [keys]}
            ).execute()
            
            # Write data
            service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"{SHEET_NAME}!A2",
                valueInputOption="USER_ENTERED",
                body={"values": [values]}
            ).execute()
            
            return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        
        raise


def save_batch(data: list, name: str, *, spreadsheet_id: str = None, credentials_path: str = None) -> str:
    """
    Save multiple records to Google Sheets.
    
    Args:
        data: List of dictionaries
        name: Directive name
        spreadsheet_id: Google Sheets spreadsheet ID
        credentials_path: Path to credentials JSON
    
    Returns:
        Spreadsheet URL
    """
    if not data:
        return ""
    
    if not GOOGLE_SHEETS_AVAILABLE:
        raise ImportError(
            "google-api-python-client not installed. "
            "Run: pip install google-api-python-client"
        )
    
    service = _get_service(credentials_path)
    spreadsheet_id = _get_spreadsheet_id(spreadsheet_id)
    
    # Collect all unique keys
    all_keys = set()
    for item in data:
        all_keys.update(item.keys())
    
    keys = list(all_keys)
    
    # Convert all data to rows
    rows = []
    for item in data:
        row = {k: str(v) for k, v in item.items()}
        rows.append([row.get(k, "") for k in keys])
    
    try:
        # Try to read existing headers
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{SHEET_NAME}!1:1"
        ).execute()
        
        existing_headers = result.get('values', [[]])[0] if result.get('values') else []
        
        if not existing_headers:
            # Write headers and data
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{SHEET_NAME}!A1",
                valueInputOption="USER_ENTERED",
                body={"values": [keys]}
            ).execute()
            
            service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"{SHEET_NAME}!A2",
                valueInputOption="USER_ENTERED",
                body={"values": rows}
            ).execute()
        else:
            # Has existing headers
            new_keys = [k for k in keys if k not in existing_headers]
            
            if new_keys:
                all_headers = existing_headers + new_keys
                service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f"{SHEET_NAME}!A1",
                    valueInputOption="USER_ENTERED",
                    body={"values": [all_headers]}
                ).execute()
            
            # Get next row
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"{SHEET_NAME}"
            ).execute()
            
            existing_rows = len(result.get('values', []))
            next_row = existing_rows + 1
            
            # Build full rows
            full_rows = []
            for item in data:
                row = {k: str(v) for k, v in item.items()}
                full_rows.append([row.get(h, "") for h in (existing_headers + new_keys)])
            
            service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"{SHEET_NAME}!A{next_row}",
                valueInputOption="USER_ENTERED",
                body={"values": full_rows}
            ).execute()
        
        return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    
    except Exception as e:
        if "not found" in str(e).lower() or "404" in str(e):
            spreadsheet = {
                'properties': {'title': f'Scrapit - {name}'},
                'sheets': [{'properties': {'title': SHEET_NAME}}]
            }
            spreadsheet = service.spreadsheets().create(
                body=spreadsheet,
                fields='spreadsheetId'
            ).execute()
            
            spreadsheet_id = spreadsheet.get('spreadsheetId')
            
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{SHEET_NAME}!A1",
                valueInputOption="USER_ENTERED",
                body={"values": [keys]}
            ).execute()
            
            service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"{SHEET_NAME}!A2",
                valueInputOption="USER_ENTERED",
                body={"values": rows}
            ).execute()
            
            return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        
        raise

import os
import json
import datetime
import requests
import gspread
from google.oauth2.service_account import Credentials

# --- Configuration & Credentials ---
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1EEvBiLzCWZewuWXlbPpqBjriCPITA0gGiVhUe5pUNrQ")
APOLLO_API_KEY = os.environ.get("APOLLO_API_KEY")  # Get free API key from apollo.io or similar provider

def get_google_sheet_client():
    if not GOOGLE_CREDS_JSON:
        raise ValueError("Missing GOOGLE_CREDENTIALS_JSON secret in GitHub Actions settings.")
    
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    try:
        creds_dict = json.loads(GOOGLE_CREDS_JSON)
    except json.JSONDecodeError as e:
        raise ValueError(f"GOOGLE_CREDENTIALS_JSON is not valid JSON. Please re-paste the full key file content. Error: {e}")
        
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(credentials)
    return client

def get_existing_emails(worksheet):
    """Fetch column 2 (Email Address) to prevent adding duplicate recruiter leads."""
    email_col = worksheet.col_values(2)
    return set(email_col[1:])  # Ignore header row

def fetch_salesforce_leads():
    leads = []
    
    # Fallback test lead if API key is not yet set or returns empty
    if not APOLLO_API_KEY:
        print("APOLLO_API_KEY not found. Generating a test recruiter lead.")
        leads.append({
            "name": "Test Recruiter",
            "email": f"test.recruiter.{datetime.datetime.now().strftime('%H%M%S')}@example.com",
            "company": "Cloud Tech Global",
            "country": "USA",
            "title": "Salesforce Developer (Part-Time)",
            "job_url": "https://linkedin.com/jobs/test-link",
            "notes": "Test automation lead"
        })
        return leads

    # ... keep the rest of your Apollo API code below ...

def main():
    print("Starting Recruiter Lead Collector Agent...")
    
    # 1. Connect to Google Sheets
    gc = get_google_sheet_client()
    sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
    
    existing_emails = get_existing_emails(sheet)
    print(f"Loaded {len(existing_emails)} existing lead emails.")

    # 2. Fetch fresh recruiter leads
    new_leads = fetch_salesforce_leads()
    today_str = datetime.date.today().isoformat()
    
    rows_to_append = []
    for lead in new_leads:
        if lead["email"] in existing_emails:
            continue  # Skip duplicates
        
        row = [
            lead["name"],
            lead["email"],
            lead["company"],
            lead["country"],
            lead["title"],
            lead["job_url"],
            today_str,
            "New",
            "",
            lead["notes"]
        ]
        rows_to_append.append(row)
        existing_emails.add(lead["email"])

    # 3. Append to Sheet
    if rows_to_append:
        sheet.append_rows(rows_to_append)
        print(f"Successfully added {len(rows_to_append)} new recruiter leads to Google Sheet.")
    else:
        print("No new unique recruiter leads found today.")

if __name__ == "__main__":
    main()

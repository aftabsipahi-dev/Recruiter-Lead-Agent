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
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_dict = json.loads(GOOGLE_CREDS_JSON)
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(credentials)
    return client

def get_existing_emails(worksheet):
    """Fetch column 2 (Email Address) to prevent adding duplicate recruiter leads."""
    email_col = worksheet.col_values(2)
    return set(email_col[1:])  # Ignore header row

def fetch_salesforce_leads():
    """
    Queries lead source (Apollo API / Hunter / RapidAPI) for recruiters/talent acquisition
    hiring Salesforce roles in US, UK, Australia, and Remote worldwide.
    """
    leads = []
    
    if not APOLLO_API_KEY:
        print("Warning: APOLLO_API_KEY not configured. Running with fallback/mock leads.")
        return leads

    url = "https://api.apollo.io/v1/mixed_people/search"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": APOLLO_API_KEY,
    }
    
    payload = {
        "q_organization_job_titles": ["Salesforce Developer", "Salesforce Consultant", "Salesforce Engineer"],
        "person_titles": ["Technical Recruiter", "Talent Acquisition Specialist", "Recruiting Manager", "Head of Hiring"],
        "person_locations": ["United States", "United Kingdom", "Australia"],
        "page": 1,
        "per_page": 25,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        data = response.json()
        
        for person in data.get("people", []):
            email = person.get("email")
            if not email:
                continue
            
            leads.append({
                "name": f"{person.get('first_name', '')} {person.get('last_name', '')}".strip(),
                "email": email,
                "company": person.get("organization", {}).get("name", "N/A"),
                "country": person.get("country", "Worldwide"),
                "title": f"Hiring: Salesforce Developer (Part-Time / Contract)",
                "job_url": person.get("linkedin_url", ""),
                "notes": f"Role: {person.get('title', 'Recruiter')}"
            })
    except Exception as e:
        print(f"Error fetching leads from API: {e}")

    return leads

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
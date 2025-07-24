# --- Imports ---
import json
import os
import base64
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from bs4 import BeautifulSoup
import requests

# --- Configuration ---
# Set your Google API key as an environment variable
# os.environ['GOOGLE_API_KEY'] = 'YOUR_API_KEY'
GMAIL_LABEL = "Your Label Name"  # The Gmail label to search for
REGISTRATIONS_FILE = r"C:\Users\cryst\RHub\Registrations\registrations.json"
GOOGLE_MASTER_FILE = r"C:\Users\cryst\RHub\Registrations\google_master.json"
CREDENTIALS_FILE = r"C:\Users\cryst\ETemplates\credentials.json"
TOKEN_FILE = 'token.json'
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# --- Functions ---

def get_gmail_service():
    """Authenticates with the Gmail API and returns a service object."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)


def get_emails_by_label(service, label_name):
    """Retrieves all unread emails with a specific label."""
    if label_name == "Your Label Name":
        print("Please update the GMAIL_LABEL variable in the script with your actual Gmail label.")
        return []

    query = f"label:\"{label_name}\" is:unread"
    results = service.users().messages().list(userId='me', q=query).execute()
    return results.get('messages', [])


def get_email_body(service, msg_id):
    """Retrieves the HTML body of a specific email."""
    msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
    payload = msg['payload']
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/html':
                data = part['body']['data']
                return base64.urlsafe_b64decode(data).decode('utf-8')
    elif 'body' in payload:
        data = payload['body']['data']
        return base64.urlsafe_b64decode(data).decode('utf-8')
    return ""


def parse_email(email_body):
    """Parses the HTML email body and extracts the restaurant's information."""
    soup = BeautifulSoup(email_body, 'html.parser')
    data = {"registration_date": datetime.now().strftime("%Y-%m-%d")}
    rows = soup.find_all('tr')
    for i in range(len(rows) - 1):
        if 'EAF2FA' in str(rows[i]):
            key_element = rows[i].find('strong')
            if key_element:
                key = key_element.get_text().strip()
                value_element = rows[i + 1].find('font')
                if value_element:
                    value = value_element.get_text().strip()
                    if key == "Restaurant Website":
                        if " - " in value:
                            parts = value.split(" - ", 1)
                            data["Restaurant Website"] = parts[0]
                            data["Web Notes"] = parts[1]
                        else:
                            data["Restaurant Website"] = value
                            data["Web Notes"] = ""
                    else:
                        data[key] = value
    return data


def get_google_place_details(restaurant_name, address):
    """Gets details for a restaurant from the Google Places API."""
    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        print("Google API key not found. Please set the GOOGLE_API_KEY environment variable.")
        return None

    url = f"https://maps.googleapis.com/maps/api/place/findplacefromtext/json?input={restaurant_name} {address}&inputtype=textquery&fields=place_id,name,formatted_address,international_phone_number,formatted_phone_number,url,website&key={api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        if data.get('status') == 'OK' and data.get('candidates'):
            return data['candidates'][0]
        else:
            print(f"Google Places API returned status: {data.get('status')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred with the Google Places API request: {e}")
        return None

def append_to_json_file(data, filename):
    """Appends data to a list in a JSON file."""
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))

    file_data = []
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        with open(filename, 'r') as f:
            try:
                file_data = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from {filename}. Starting with a new list.")
                file_data = []

    if not isinstance(file_data, list):
        print(f"Warning: Existing data in {filename} is not a list. Overwriting with a new list.")
        file_data = []

    file_data.append(data)

    with open(filename, 'w') as f:
        json.dump(file_data, f, indent=4)


def process_emails():
    """
    Main function to process registration emails.
    - Fetches unread emails from a specified Gmail label.
    - Parses email content to extract registration data.
    - Saves registration data to a JSON file.
    - Fetches additional details from Google Places API.
    - Saves Google Places data to another JSON file.
    - Marks the email as read.
    """
    service = get_gmail_service()
    messages = get_emails_by_label(service, GMAIL_LABEL)

    if not messages:
        print("No unread registration emails found.")
        return

    print(f"Found {len(messages)} new registration emails.")

    for message in messages:
        msg_id = message['id']
        email_body = get_email_body(service, msg_id)

        if email_body:
            registration_data = parse_email(email_body)
            print(f"Processing registration for: {registration_data.get('Restaurant Name')}")

            # Save registration data
            append_to_json_file(registration_data, REGISTRATIONS_FILE)
            print(f"Saved registration data to {REGISTRATIONS_FILE}")

            # Get and save Google Places details
            name = registration_data.get("Restaurant Name")
            address = registration_data.get("Restaurant Address")
            if name and address:
                google_details = get_google_place_details(name, address)
                if google_details:
                    append_to_json_file(google_details, GOOGLE_MASTER_FILE)
                    print(f"Saved Google Places data to {GOOGLE_MASTER_FILE}")

            # Mark email as read by removing the 'UNREAD' label
            service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()
            print(f"Marked email {msg_id} as read.")

# --- Main Execution ---
# This block allows the script to be run directly or imported into a Jupyter notebook.
if __name__ == '__main__':
    # To run in a Jupyter notebook, you can call process_emails() directly.
    # Make sure to set your GOOGLE_API_KEY environment variable first.
    # Example:
    # import os
    # os.environ['GOOGLE_API_KEY'] = 'YOUR_API_KEY'
    # process_emails()

    # Check if the API key is set before running
    if not os.environ.get('GOOGLE_API_KEY'):
        print("Please set the 'GOOGLE_API_KEY' environment variable before running the script.")
    else:
        process_emails()

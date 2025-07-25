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
import urllib.parse
from unidecode import unidecode
import html
import difflib

# --- Configuration ---
# Set your Google API key as an environment variable
os.environ['GOOGLE_API_KEY'] = ''
GMAIL_LABEL = "Registrations"  # The Gmail label to search for
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


def remove_macrons(input_string):
    """Removes macrons from a string."""
    return unidecode(input_string)

def parse_email(email_body):
    """Parses the HTML email body and extracts the restaurant's information."""
    soup = BeautifulSoup(email_body, 'html.parser')
    data = {"registration_date": datetime.now().strftime("%Y-%m-%d")}
    rows = soup.find_all('tr')
    for i in range(len(rows) - 1):
        if 'EAF2FA' in str(rows[i]):
            key_element = rows[i].find('strong')
            if key_element:
                key = remove_macrons(key_element.get_text().strip())
                value_element = rows[i + 1].find('font')
                if value_element:
                    value = remove_macrons(value_element.get_text().strip())
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
    """Gets full details for a restaurant using Google Places API in two steps."""
    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        print("Google API key not found. Please set the GOOGLE_API_KEY environment variable.")
        return None

    encoded_input = urllib.parse.quote(f"{restaurant_name} {address}")

    # Step 1: Find Place
    find_url = f"https://maps.googleapis.com/maps/api/place/findplacefromtext/json?input={encoded_input}&inputtype=textquery&fields=place_id,name,formatted_address&key={api_key}"
    try:
        find_response = requests.get(find_url)
        find_response.raise_for_status()
        find_data = find_response.json()

        if find_data.get('status') == 'OK' and find_data.get('candidates'):
            place_id = find_data['candidates'][0]['place_id']

            # Step 2: Get Details
            details_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=place_id,name,formatted_address,international_phone_number,formatted_phone_number,url,website&key={api_key}"
            detail_response = requests.get(details_url)
            detail_response.raise_for_status()
            detail_data = detail_response.json()

            if detail_data.get('status') == 'OK':
                return detail_data['result']
            else:
                print(f"Place Details error: {detail_data.get('status')}")
                return None
        else:
            print(f"Find Place error: {find_data.get('status')}")
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
        with open(filename, 'r', encoding='utf-8') as f:
            try:
                file_data = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from {filename}. Starting with a new list.")
                file_data = []

    if not isinstance(file_data, list):
        print(f"Warning: Existing data in {filename} is not a list. Overwriting with a new list.")
        file_data = []

    file_data.append(data)

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(file_data, f, indent=4, ensure_ascii=False)


def compare_data(reg_data, google_data):
    """Compares the registration data and google data and returns True if they are a close match."""
    if not reg_data or not google_data:
        return False

    name_match = difflib.SequenceMatcher(None, reg_data.get("Restaurant Name", ""), google_data.get("name", "")).ratio() > 0.8
    address_match = difflib.SequenceMatcher(None, reg_data.get("Restaurant Address", ""), google_data.get("formatted_address", "")).ratio() > 0.8
    phone_match = difflib.SequenceMatcher(None, reg_data.get("Restaurant Phone Number", ""), google_data.get("formatted_phone_number", "")).ratio() > 0.8
    website_match = difflib.SequenceMatcher(None, reg_data.get("Restaurant Website", ""), google_data.get("website", "")).ratio() > 0.8

    return name_match and address_match and phone_match and website_match

def get_label_id(service, label_name):
    """Retrieves the ID of a label, creating it if it doesn't exist."""
    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    for label in labels:
        if label['name'] == label_name:
            return label['id']
    # Label doesn't exist, so create it.
    label_body = {'name': label_name, 'labelListVisibility': 'labelShow', 'messageListVisibility': 'show'}
    created_label = service.users().labels().create(userId='me', body=label_body).execute()
    print(f"Created label: {created_label['name']}")
    return created_label['id']

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
    new_label_name = "Registrations/Complete Registrations"
    complete_label_id = get_label_id(service, new_label_name)
    registrations_label_id = get_label_id(service, "Registrations")
    messages = get_emails_by_label(service, "Registrations")

    if not messages:
        print("No unread registration emails found.")
        return

    print(f"Found {len(messages)} new registration emails.")

    # Load existing registrations
    existing_registrations = []
    if os.path.exists(REGISTRATIONS_FILE) and os.path.getsize(REGISTRATIONS_FILE) > 0:
        with open(REGISTRATIONS_FILE, 'r', encoding='utf-8') as f:
            try:
                existing_registrations = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from {REGISTRATIONS_FILE}. Starting with a new list.")
                existing_registrations = []

    for message in messages:
        msg_id = message['id']
        email_body = get_email_body(service, msg_id)

        if email_body:
            registration_data = parse_email(email_body)
            print(f"Processing registration for: {registration_data.get('Restaurant Name')}")

            # Check for existing entry
            match_found = False
            for entry in existing_registrations:
                if entry.get("Restaurant Name") == registration_data.get("Restaurant Name") and entry.get("Restaurant Address") == registration_data.get("Restaurant Address"):
                    match_found = True
                    updated_fields = []
                    for key, value in registration_data.items():
                        if entry.get(key) != value:
                            updated_fields.append(key)
                            entry[key] = value

                    if updated_fields:
                        print(f"Restaurant {registration_data.get('Restaurant Name')} has already registered. The following information was updated: {', '.join(updated_fields)}")
                    else:
                        print(f"Restaurant {registration_data.get('Restaurant Name')} has already registered. No new information to update.")

                    break

            if not match_found:
                # Get and save Google Places details
                name = registration_data.get("Restaurant Name")
                address = registration_data.get("Restaurant Address")
                if name and address:
                    google_details = get_google_place_details(name, address)
                    if google_details:
                        place_id = google_details.get('place_id')
                        registration_data['place_id'] = place_id
                        cleaned_details = {'place_id': place_id}
                        for key, value in google_details.items():
                            if isinstance(value, str):
                                if key == 'name':
                                    cleaned_details[key] = remove_macrons(value)
                                else:
                                    cleaned_details[key] = html.escape(value)
                            else:
                                cleaned_details[key] = value
                        choice = "1"
                        if not compare_data(registration_data, google_details):
                            print(f"Data for {registration_data.get('Restaurant Name')} does not match.\n")
                        
                            # Show differences field by field
                            compare_fields = [
                                ("Restaurant Name", "name"),
                                ("Restaurant Address", "formatted_address"),
                                ("Restaurant Phone Number", "formatted_phone_number"),
                                ("Restaurant Website", "website")
                            ]
                            print("Differences found:")
                            for reg_key, google_key in compare_fields:
                                reg_val = registration_data.get(reg_key, "")
                                google_val = google_details.get(google_key, "")
                                if reg_val != google_val:
                                    print(f"- {reg_key}:\n    Registration: {reg_val}\n    Google:       {google_val}\n")
                        
                            print("1. Use Google version")
                            print("2. Use Registration version")
                            choice = input("Please choose which version to use: ")

                        # Save user's choice
                        choice_file_dir = os.path.join(r"C:\Users\cryst\ETemplates\Completed Templates", registration_data.get("Restaurant Name"))
                        if not os.path.exists(choice_file_dir):
                            os.makedirs(choice_file_dir)
                        choice_file_path = os.path.join(choice_file_dir, f"{registration_data.get('Restaurant Name')}.json")
                        with open(choice_file_path, 'w', encoding='utf-8') as f:
                            json.dump({"choice": choice}, f, indent=4)

                        append_to_json_file(google_details, GOOGLE_MASTER_FILE)
                        print(f"Saved Google Places data to {GOOGLE_MASTER_FILE}")

                        # Create final JSON
                        # Extract region and zip safely
                        region_part = ""
                        zip_code = ""
                        
                        if len(google_details.get("formatted_address", "").split(',')) > 2:
                            region_text = google_details.get("formatted_address").split(',')[2].strip()
                            parts = region_text.split()
                            if parts and parts[-1].isdigit():
                                zip_code = parts[-1]
                                region_part = " ".join(parts[:-1])
                            else:
                                region_part = region_text
                        
                        final_data = {
                            "plac_id": google_details.get("place_id"),
                            "rName": google_details.get("name"),
                            "rAddress": google_details.get("formatted_address"),
                            "rCity": google_details.get("formatted_address").split(',')[1].strip() if len(google_details.get("formatted_address", "").split(',')) > 1 else "",
                            "rRegion": region_part,
                            "rZip": zip_code,
                            "rPhone": google_details.get("formatted_phone_number"),
                            "rIntPhone": google_details.get("international_phone_number"),
                            "rEmail": registration_data.get("Restaurant Email"),
                            "rWebsite": google_details.get("website"),
                            "rMaps link": google_details.get("url")
                        }

                        final_file_dir = os.path.join(r"C:\Users\cryst\ETemplates\Completed Templates", registration_data.get("Restaurant Name"))
                        if not os.path.exists(final_file_dir):
                            os.makedirs(final_file_dir)
                        final_file_path = os.path.join(final_file_dir, f"{registration_data.get('Restaurant Name')}.json")
                        with open(final_file_path, 'w', encoding='utf-8') as f:
                            json.dump(final_data, f, indent=4, ensure_ascii=False)

                existing_registrations.append(registration_data)

            # Save updated registrations data
            with open(REGISTRATIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(existing_registrations, f, indent=4, ensure_ascii=False)

            # Mark email as read by removing the 'UNREAD' and old labels, and adding the new one
            service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD', registrations_label_id], 'addLabelIds': [complete_label_id]}).execute()
            print(f"Marked email {msg_id} as read and moved to {new_label_name}.")

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

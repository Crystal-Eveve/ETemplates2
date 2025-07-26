# --- Imports ---
import json
import os
import re
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
import sys

# Path to generate_config
sys.path.append(r"C:\Users\cryst\ETemplates")
from generate_config import create_config_from_json

# --- Configuration ---
os.environ['GOOGLE_API_KEY'] = 'AIzaSyB8LApRoYoZWnZcdGnVFXobjy18AZr55Go'
GMAIL_LABEL = "Registrations"
REGISTRATIONS_FILE = r"C:\Users\cryst\RHub\Registrations\registrations.json"
GOOGLE_MASTER_FILE = r"C:\Users\cryst\RHub\Registrations\google_master.json"
CREDENTIALS_FILE = r"C:\Users\cryst\ETemplates\credentials.json"
TOKEN_FILE = 'token.json'
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

GOOGLE_CSE_KEY = "AIzaSyCHrZ3rxoWF7skrRKjUr_0Ysq3BiOY6ggA"
GOOGLE_CSE_ID = "f58e890e9129142c6"

# --- Helpers ---
def split_city_zip(address_segment: str):
    if not address_segment:
        return "", ""
    parts = address_segment.strip().split()
    if parts and parts[-1].isdigit():
        return " ".join(parts[:-1]), parts[-1]
    return address_segment.strip(), ""

def normalize(text):
    return re.sub(r'[^a-z0-9 ]', '', text.lower())

def fallback_social_from_website(website_url, domain_keyword):
    try:
        if not website_url:
            return ""
        resp = requests.get(website_url, timeout=8)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if domain_keyword in href:
                return href.split("?")[0]
    except Exception:
        pass
    return ""

def find_social_link(restaurant_name, city, domain, website_url=None):
    if not GOOGLE_CSE_KEY or not GOOGLE_CSE_ID:
        return ""
    search_domain = "tripadvisor.co.nz" if "tripadvisor" in domain else domain
    query = f'"{restaurant_name}" "{city}" site:{search_domain}'
    url = (f"https://www.googleapis.com/customsearch/v1"
           f"?key={GOOGLE_CSE_KEY}&cx={GOOGLE_CSE_ID}&q={urllib.parse.quote(query)}")
    norm_name = normalize(restaurant_name)
    norm_city = normalize(city)
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        for item in items:
            link = item.get("link", "")
            title = normalize(item.get("title", ""))
            snippet = normalize(item.get("snippet", ""))

            if "tripadvisor" in domain and "/Restaurant_Review-" not in link:
                continue
            if "facebook" in domain:
                bad_patterns = ["/events/", "/groups/", "/watch/", "/gaming/", "/marketplace/"]
                if any(b in link for b in bad_patterns):
                    continue
                if not any(word in link.lower() for word in norm_name.split()):
                    continue
            if "instagram" in domain:
                if "/p/" in link or "/reel/" in link:
                    continue
            if norm_name.split()[0] not in title and norm_name.split()[0] not in snippet:
                continue
            if norm_city not in title and norm_city not in snippet:
                continue
            return link
    except Exception as e:
        print(f"Error fetching {domain} link: {e}")
    if website_url:
        fallback = fallback_social_from_website(website_url, domain)
        if fallback:
            print(f"Fallback found for {domain}: {fallback}")
            return fallback
    return ""

# Gmail and parsing
def get_gmail_service():
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
    query = f"label:\"{label_name}\" is:unread"
    results = service.users().messages().list(userId='me', q=query).execute()
    return results.get('messages', [])

def get_email_body(service, msg_id):
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
    return unidecode(input_string)

def parse_email(email_body):
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
    api_key = os.environ.get('GOOGLE_API_KEY')
    encoded_input = urllib.parse.quote(f"{restaurant_name} {address}")
    find_url = (
        "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        f"?input={encoded_input}"
        "&inputtype=textquery"
        "&fields=place_id,name,formatted_address"
        "&locationbias=rectangle:-47.5,166.0|-34.0,179.0"
        "&region=nz"
        f"&key={api_key}"
    )
    try:
        find_response = requests.get(find_url)
        find_response.raise_for_status()
        find_data = find_response.json()
        if find_data.get('status') == 'OK' and find_data.get('candidates'):
            place_id = find_data['candidates'][0]['place_id']
            details_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=place_id,name,formatted_address,international_phone_number,formatted_phone_number,url,website&key={api_key}"
            detail_response = requests.get(details_url)
            detail_response.raise_for_status()
            detail_data = detail_response.json()
            if detail_data.get('status') == 'OK':
                return detail_data['result']
    except requests.exceptions.RequestException as e:
        print(f"An error occurred with the Google Places API request: {e}")
    return None

def append_to_json_file(data, filename):
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    file_data = []
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        with open(filename, 'r', encoding='utf-8') as f:
            try:
                file_data = json.load(f)
            except json.JSONDecodeError:
                file_data = []
    if not isinstance(file_data, list):
        file_data = []
    file_data.append(data)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(file_data, f, indent=4, ensure_ascii=False)

def compare_data(reg_data, google_data):
    if not reg_data or not google_data:
        return False
    return (
        difflib.SequenceMatcher(None, reg_data.get("Restaurant Name", ""), google_data.get("name", "")).ratio() > 0.8
        and difflib.SequenceMatcher(None, reg_data.get("Restaurant Address", ""), google_data.get("formatted_address", "")).ratio() > 0.8
        and difflib.SequenceMatcher(None, reg_data.get("Restaurant Phone Number", ""), google_data.get("formatted_phone_number", "")).ratio() > 0.8
        and difflib.SequenceMatcher(None, reg_data.get("Restaurant Website", ""), google_data.get("website", "")).ratio() > 0.8
    )

def get_label_id(service, label_name):
    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    for label in labels:
        if label['name'] == label_name:
            return label['id']
    label_body = {'name': label_name, 'labelListVisibility': 'labelShow', 'messageListVisibility': 'show'}
    created_label = service.users().labels().create(userId='me', body=label_body).execute()
    return created_label['id']

# --- Main process ---
def process_emails():
    service = get_gmail_service()
    new_label_name = "Registrations/Complete Registrations"
    complete_label_id = get_label_id(service, new_label_name)
    registrations_label_id = get_label_id(service, "Registrations")
    messages = get_emails_by_label(service, "Registrations")
    if not messages:
        print("No unread registration emails found.")
        return
    print(f"Found {len(messages)} new registration emails.")

    existing_registrations = []
    if os.path.exists(REGISTRATIONS_FILE) and os.path.getsize(REGISTRATIONS_FILE) > 0:
        with open(REGISTRATIONS_FILE, 'r', encoding='utf-8') as f:
            try:
                existing_registrations = json.load(f)
            except json.JSONDecodeError:
                existing_registrations = []

    for message in messages:
        msg_id = message['id']
        email_body = get_email_body(service, msg_id)
        if not email_body:
            continue

        registration_data = parse_email(email_body)
        print(f"Processing registration for: {registration_data.get('Restaurant Name')}")

        # Prevent duplicate entries
        if any(entry.get("Restaurant Name") == registration_data.get("Restaurant Name") and entry.get("Restaurant Address") == registration_data.get("Restaurant Address") for entry in existing_registrations):
            continue

        google_details = get_google_place_details(
            registration_data.get("Restaurant Name"), registration_data.get("Restaurant Address")
        )
        if google_details:
            # Show diffs
            compare_fields = [
                ("Restaurant Name", "name"),
                ("Restaurant Address", "formatted_address"),
                ("Restaurant Phone Number", "formatted_phone_number"),
                ("Restaurant Website", "website"),
            ]
            diffs = [
                (reg_key, google_details.get(google_key, ""), registration_data.get(reg_key, ""))
                for reg_key, google_key in compare_fields
                if registration_data.get(reg_key, "") != google_details.get(google_key, "")
            ]
            if diffs:
                print("Differences found:")
                for field, g_val, r_val in diffs:
                    print(f"- {field}:\n    Google:       {g_val}\n    Registration: {r_val}\n")

            google_phone = google_details.get("formatted_phone_number", "")
            google_website = google_details.get("website", "")
            auto_choose_2 = (not google_phone and registration_data.get("Restaurant Phone Number")) or \
                            (not google_website and registration_data.get("Restaurant Website"))
            print("1. Use Google version")
            print("2. Use Registration version")
            choice = input("Please choose which version to use (default 2 if missing phone/website): ") or ("2" if auto_choose_2 else "1")

            choice_file_dir = os.path.join(r"C:\Users\cryst\ETemplates\Completed Templates", registration_data["Restaurant Name"])
            os.makedirs(choice_file_dir, exist_ok=True)
            choice_file_path = os.path.join(choice_file_dir, f"{registration_data['Restaurant Name']}.json")
            with open(choice_file_path, 'w', encoding='utf-8') as f:
                json.dump({"choice": choice}, f, indent=4)

            if choice.strip() == "2":
                # Registration data
                addr = registration_data.get("Restaurant Address", "")
                parts = addr.split(',')
                r_region = registration_data.get("Restaurant Region", "")
                r_city, r_zip = ("", "")
                if len(parts) > 1:
                    r_city, r_zip = split_city_zip(parts[1])

                site = (registration_data.get("Restaurant Website") or "").strip().rstrip("/")
                if site and not site.startswith(("http://", "https://")):
                    site = "https://" + site
                site = site.replace("http://", "https://")

                final_data = {
                    "plac_id": "",
                    "rName": registration_data.get("Restaurant Name", ""),
                    "rAddress": addr,
                    "rCity": r_city,
                    "rRegion": r_region,
                    "rZip": r_zip,
                    "rPhone": registration_data.get("Restaurant Phone Number"),
                    "rIntPhone": registration_data.get("Restaurant Phone Number"),
                    "rEmail": registration_data.get("Restaurant Email"),
                    "rWebsite": site,
                    "rMaps link": "",
                    "socialFacebook": "",
                    "socialInstagram": "",
                    "socialTripadvisor": ""
                }

            else:
                # Google data
                formatted_parts = google_details.get("formatted_address", "").split(',')
                r_city, r_zip = ("", "")
                if len(formatted_parts) > 1:
                    r_city, r_zip = split_city_zip(formatted_parts[1])
                region_part = formatted_parts[2].strip() if len(formatted_parts) > 2 else ""

                raw_phone = google_details.get("formatted_phone_number", "") or ""
                if raw_phone and not raw_phone.startswith("+64"):
                    cleaned = raw_phone.replace("+64", "").strip()
                    if not cleaned.startswith("0"):
                        cleaned = "0" + cleaned
                    raw_phone = f"+64 {cleaned}"

                final_data = {
                    "plac_id": google_details.get("place_id"),
                    "rName": google_details.get("name"),
                    "rAddress": google_details.get("formatted_address"),
                    "rCity": r_city,
                    "rRegion": region_part,
                    "rZip": r_zip,
                    "rPhone": raw_phone,
                    "rIntPhone": google_details.get("international_phone_number"),
                    "rEmail": registration_data.get("Restaurant Email"),
                    "rWebsite": google_details.get("website"),
                    "rMaps link": google_details.get("url"),
                }

                facebook = find_social_link(final_data["rName"], final_data["rCity"], "facebook.com", final_data.get("rWebsite"))
                instagram = find_social_link(final_data["rName"], final_data["rCity"], "instagram.com", final_data.get("rWebsite"))
                tripadvisor = find_social_link(final_data["rName"], final_data["rCity"], "tripadvisor.com", final_data.get("rWebsite"))
                final_data["socialFacebook"] = facebook
                final_data["socialInstagram"] = instagram
                final_data["socialTripadvisor"] = tripadvisor

                website = (final_data.get("rWebsite") or "").strip().rstrip("/")
                if website and not website.startswith(("http://", "https://")):
                    website = "https://" + website
                website = website.replace("http://", "https://")
                final_data["rWebsite"] = website

            final_file_path = os.path.join(choice_file_dir, f"{registration_data['Restaurant Name']}.json")
            with open(final_file_path, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, indent=4, ensure_ascii=False)
            create_config_from_json(final_file_path)

        existing_registrations.append(registration_data)

        with open(REGISTRATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing_registrations, f, indent=4, ensure_ascii=False)

        service.users().messages().modify(
            userId='me', id=msg_id,
            body={'removeLabelIds': ['UNREAD', registrations_label_id], 'addLabelIds': [complete_label_id]}
        ).execute()
        print(f"Marked email {msg_id} as read and moved to {new_label_name}.")

if __name__ == '__main__':
    if not os.environ.get('GOOGLE_API_KEY'):
        print("Please set the 'GOOGLE_API_KEY' environment variable before running the script.")
    else:
        process_emails()

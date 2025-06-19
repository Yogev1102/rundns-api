import imaplib
import email
import xml.etree.ElementTree as ET
import requests
from email.header import decode_header
from datetime import datetime
import time

# פרטי התחברות לתיבת Zoho
IMAP_SERVER = 'imap.zoho.com'
EMAIL_ACCOUNT = 'reports@rundns.io'
EMAIL_PASSWORD = 'zQi7J1NQPEmm'

# פרטי Base44
API_KEY = '7a3f0220b8b84b279120295c42ab068e'
COLLECTION = 'DMARC_Reports'
API_URL = "https://rundns-server.onrender.com"

# הגדרות באצ'ים
BATCH_SIZE = 200
BATCH_DELAY_SECONDS = 3

def parse_dmarc_xml(xml_string):
    data = []
    root = ET.fromstring(xml_string)
    report_metadata = root.find("report_metadata")
    policy_published = root.find("policy_published")

    for record in root.findall("record"):
        row = {
            "Report ID": report_metadata.findtext("report_id", ""),
            "Organization": report_metadata.findtext("org_name", ""),
            "Reporter Email": report_metadata.findtext("email", ""),
            "Date Range": f"{report_metadata.findtext('date_range/begin')} to {report_metadata.findtext('date_range/end')}",
            "Processed Date": "",
            "Source IP": record.findtext("row/source_ip", ""),
            "Provider": "",
            "Header From": record.findtext("identifiers/header_from", ""),
            "Email Count": record.findtext("row/count", ""),
            "Policy Domain": policy_published.findtext("domain", ""),
            "Main Policy (p)": policy_published.findtext("p", ""),
            "Subdomain Policy (sp)": policy_published.findtext("sp", ""),
            "DKIM/SPF Alignment": f"{policy_published.findtext('adkim', '')}/{policy_published.findtext('aspf', '')}",
            "Policy % (pct)": policy_published.findtext("pct", ""),
            "Disposition": record.findtext("row/policy_evaluated/disposition", ""),
            "DKIM": record.findtext("row/policy_evaluated/dkim", ""),
            "SPF": record.findtext("row/policy_evaluated/spf", ""),
            "created_at": datetime.now().isoformat()
        }
        data.append(row)
    return data

def send_to_base44(row):
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json',
        'User-Agent': 'RunDNS-Processor/1.0'
    }
    response = requests.post(API_URL, headers=headers, json=row)
    print(f"📤 שלחתי ל־Base44: סטטוס {response.status_code}")
    return response.status_code == 200

def check_mail():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    mail.select("inbox")

    typ, msgnums = mail.search(None, 'UNSEEN')
    all_msg_ids = msgnums[0].split()
    print(f"📬 נמצאו {len(all_msg_ids)} מיילים לא נקראו")

    for i in range(0, len(all_msg_ids), BATCH_SIZE):
        batch = all_msg_ids[i:i + BATCH_SIZE]
        print(f"🚀 מעבד באצ' {i // BATCH_SIZE + 1} מתוך {((len(all_msg_ids) - 1) // BATCH_SIZE) + 1}")

        for num in batch:
            typ, msg_data = mail.fetch(num, '(RFC822)')
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            for part in msg.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue

                filename = part.get_filename()
                if filename and filename.endswith(".xml"):
                    payload = part.get_payload(decode=True)
                    try:
                        rows = parse_dmarc_xml(payload.decode())
                        for row in rows:
                            send_to_base44(row)
                    except Exception as e:
                        print(f"❌ שגיאה בקריאת XML: {e}")

            mail.store(num, '+FLAGS', '\\Seen')

        print(f"⏳ ממתין {BATCH_DELAY_SECONDS} שניות לפני באצ' הבא...")
        time.sleep(BATCH_DELAY_SECONDS)

    mail.logout()

# התחלת תהליך
if __name__ == "__main__":
    print("🔍 בודק תיבה...")
    check_mail()

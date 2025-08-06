from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.auth.exceptions import InvalidValue
import requests
from django.conf import settings
import time
from datetime import datetime
import resend
import traceback




resend_api_key = settings.RESEND_API_KEY
frontend_base_url = settings.FRONTEND_BASE_URL
    
 #send reset email for the user's email 
resend.api_key = resend_api_key
def send_contact_email(from_name, from_email, subject, message):
    to_email = "emmanuel0058@gmail.com"  # replace with your organization's receiving email

    html_content = f"""
        <p>You have received a new contact form submission:</p>
        <ul>
            <li><strong>Name:</strong> {from_name}</li>
            <li><strong>Email:</strong> {from_email}</li>
            <li><strong>Subject:</strong> {subject}</li>
            <li><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
        </ul>
        <p><strong>Message:</strong></p>
        <p>{message}</p>
    """

    params = {
        "from": "ScriptReadr Contact <onboarding@resend.dev>",
        "to": to_email,
        "subject": f"Contact Form Submission: {subject}",
        "html": html_content
    }

    try:
        email = resend.Emails.send(params)
        print(email)
        return True, None
    except Exception as e:
        print(f"[Resend Error] {str(e)}")
        traceback.print_exc()
        return False, str(e)

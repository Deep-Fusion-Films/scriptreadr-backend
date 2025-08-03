from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.auth.exceptions import InvalidValue
import requests
from django.conf import settings
import time
import resend





client_id = settings.GOOGLE_CLIENT_ID
client_secret = settings.GOODLE_CLIENT_SECRET
resend_api_key = settings.RESEND_API_KEY
frontend_base_url = settings.FRONTEND_BASE_URL




def authenticate_google_user(code):
    # Step 1: Exchange code for tokens
    token_url = 'https://oauth2.googleapis.com/token'
    data = {
        'code': code,
        'client_id':client_id,
        'client_secret': client_secret,
        'redirect_uri': 'postmessage',  # for installed apps (like React frontend)
        'grant_type': 'authorization_code',
    }

    token_response = requests.post(token_url, data=data)
    if token_response.status_code != 200:
        raise Exception('Failed to exchange code for tokens')

    tokens = token_response.json()
    id_token_str = tokens['id_token']

    # Step 2: Verify ID token
    request = google_requests.Request()
    
    try:
        id_info = id_token.verify_oauth2_token(
        id_token_str,
        request,
        client_id
    )

    except InvalidValue as e:
        if "Token used too early" in str(e):
            time.sleep(2)
            id_info = id_token.verify_oauth2_token(
            id_token_str,
            request,
            client_id
            )
        else:
            raise

    return id_info
    
    
 #send reset email for the user's email 
resend.api_key = resend_api_key
def send_reset_email(to_email, token):
    reset_url = f"{frontend_base_url}/resetpassword/{token}"
    html_content = f"""
        <p>Click the link below to reset your password:</p>
        <a href="{reset_url}">{reset_url}</a>"""
        
    params = resend.Emails.SendParams = {
        "from": "ScriptReadr <onboarding@resend.dev>",
        "to": to_email,
        "subject": "Reset your password",
        "html": html_content
    }

    email = resend.Emails.send(params)
    print(email)

    
from celery import shared_task
from django.conf import settings
from io import BytesIO
import requests
import json
from django.db import close_old_connections
from user.models import User, Audio, UserSubscription
from google.cloud import storage
from google.api_core.exceptions import GoogleAPIError
from django.core.exceptions import ObjectDoesNotExist
from uuid import uuid4



elevenlabs_api_key=settings.ELEVEN_LABS_API_KEY

@shared_task(bind=True)
def process_script_audio(self, dialogues, speaker_voices, file_name, user_email):
    
    uploaded_file_name=file_name
    
    close_old_connections()
    
    try:
        user = User.objects.get(email=user_email)
    except ObjectDoesNotExist:
        return {
            "status": "failed",
            "error": "User not found"}
    
    try:
        subscription = UserSubscription.objects.get(user=user)
    except UserSubscription.DoesNotExist:
        return {
            "status": "failed",
            "error": "User subscription not found"}
    
    final_audio = BytesIO()
    total = len(dialogues)
    
    try:
        for i, dialogue in enumerate(dialogues):
            speaker = dialogue.get("speaker", "").strip()
            text = dialogue.get("text", "").strip()
            if not speaker or not text:
                continue
            voice_id = speaker_voices.get(speaker) or settings.VOICE_ID

            #call elevenlabs api
            response = requests.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream",
                    headers={
                        "xi-api-key":elevenlabs_api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "text": text,
                        "voice_settings": {
                        "stability": 0.75,
                        "similarity_boost": 0.75
                        }
                    },
                    stream=True
                )
            if response.status_code != 200:
                subscription.audio_remaining +=1
                subscription.save()
                return {
                    "status": "failed",
                    "error": "Failed to generate audio from Eleven labs, please try again.", "details": response.text}
            
            #append chunk to buffer
            for chunk in response.iter_content(chunk_size=8192):
                final_audio.write(chunk)
            
            self.update_state(
                state = 'PROGRESS',
                meta = {
                    'current': i + 1,
                    'total': total,
                    'percent': int((i + 1) / total * 100)
                }
            )
    except Exception as e:
        subscription.audio_remaining +=1
        subscription.save()
        return {
            "status": "failed",
            "error": "Failed to generate audio, please try again", "details": str(e)}
    close_old_connections()
    try:
        if settings.GOOGLE_CLOUD_CREDENTIALS:
            client = storage.Client(credentials=settings.GOOGLE_CLOUD_CREDENTIALS)
        else:
            client = storage.Client()
        bucket = client.bucket(settings.GCS_BUCKET_NAME)
        filename = f"processed_audio/{user.email}_{uuid4().hex}_processed_audio.mp3"
        blob = bucket.blob(filename)
        
        #ensure pointer is at the start before upload 
        final_audio.seek(0)
        
        close_old_connections()
        blob.upload_from_file(
            final_audio,
            content_type="audio/mpeg"
            )
    except GoogleAPIError as e:
        subscription.audio_remaining +=1
        subscription.save()
        return {
            "status":"failed",
            "error": "Could not get audio from google cloud, please refresh or try again."}
    
    close_old_connections()
    #Update or create the UploadedFile record (depends on your lagic)
    # processed_script = Audio.objects.filter(user=user).order_by('-uploaded_at').first()
    
    # if  processed_script:
    #     processed_script.processed_script = filename
    #     processed_script.save()
    # else:
    Audio.objects.create(
            user=user,
            processed_audio=filename,
            audio_name = uploaded_file_name
        )
        
    close_old_connections()
    return {"status": "success"}
        

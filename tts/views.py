from django.http import StreamingHttpResponse, HttpResponse
from rest_framework .views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
from rest_framework_simplejwt.authentication import JWTAuthentication
import re
from io import BytesIO
from user.models import Audio
from google.cloud import storage
from utils.generic_script_parser import parse_script_generic
from django.conf import settings
from .tasks import process_script_audio
from celery.result import AsyncResult
from time import sleep
from user.models import UserSubscription
from django.utils import timezone



# Create your views here.


def sanitize_for_tts(text: str) -> str:
    chars_to_remove = ['*', '_', '`', '~']
    for ch in chars_to_remove:
        text = text.replace(ch, '')
    return text



class SubscriptionStatusView(APIView):
    authentication_classes = [JWTAuthentication]
    
    def get(self, request):
        
        user = request.user
        
        try:
           subscription = UserSubscription.objects.get(user=user)
           if not subscription.is_active or (subscription.current_period_end and subscription.current_period_end < timezone.now()):
               return Response(
                   {"error": "You do not have an active subscription or your subscription has expired."},
                   status=status.HTTP_403_FORBIDDEN
               )
               
            #check scripts_remaining before allowing upload
           if subscription.audio_remaining <= 0:
                return Response({"error": "You have reached your audio generation limit, you can buy another subscription to reset."},
                        status=status.HTTP_403_FORBIDDEN)
       
        except UserSubscription.DoesNotExist: 
           return Response(
               {"error": "You do not have an active subscription."},
               status=status.HTTP_403_FORBIDDEN
           )
           
        return Response({"success": "user has subscription"}, status=status.HTTP_200_OK)
        
           


#test to speech class
class Tts(APIView):
    #get all voices
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        
        # voice_id = "21m00Tcm4TlvDq8ikWAM"  # Default ElevenLabs voice
        elevenlabs_api_key= settings.ELEVEN_LABS_API_KEY

        try:
            response = requests.get(
                "https://api.elevenlabs.io/v1/voices",
                headers={
                    "xi-api-key": elevenlabs_api_key
                }
            )
            
            if response.status_code != 200:
                return Response({"error": "failed to fetch voices", "details":response.text},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
            voices = response.json().get("voices",[])
            voice_options = [{"id": v["voice_id"], "name": v["name"]} for v in voices]
            return Response(voice_options)
    
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        #post selected voices route
    def post(self, request):
        user = request.user
        
       
        subscription = UserSubscription.objects.get(user=user)

        #decrement scripts remaining by 1
        subscription.audio_remaining -=1
        subscription.save()    
        
        
        input_text = request.data.get('text')
        
        # voice_id = request.data.get("voice_id") or settings.VOICE_ID  # Default ElevenLabs voice
        speaker_voices = request.data.get('speaker_voices')
        
        
        if not input_text:
            subscription.audio_remaining -=1
            subscription.save() 
            return Response({"error": "No text provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        cleaned_text = sanitize_for_tts(input_text)        
       
        dialogues = parse_script_generic(cleaned_text)
        
        print(dialogues)
        
        task = process_script_audio.delay(dialogues,speaker_voices,user.email)
    
        print('the task id is:' + task.id)
        return Response({"task_id": task.id}, status=200)
            
        
class TaskStatusView(APIView): 
    def get(self, request, task_id):
        result = AsyncResult(task_id)
        
        response_data = ({
            "task_id": task_id,
            "status": result.status,
        })
        
        if result.status == "PROGRESS":
            progress = result.result or {}
            response_data["progress"] = progress.get("percent", 0)
            
        elif result.status == "SUCCESS":
            response_data.update(result.result or {})
        
        elif result.status == "FAILURE":
            response_data["error"] = str(result.result)
        
        return Response(response_data)



class CancelAudioTaskAPIView(APIView):
    def post(self, request):
        task_id = request.data.get("task_id")
        if not task_id:
            return Response({"detail": "Task ID is required"}, status=400)
        
        result = AsyncResult(task_id)
        result.revoke(terminate=True, signal='SIGTERM')
        
        return Response({"detail": "Task revoked"})
    
    



class ProcessedAudioView(APIView):
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        user = request.user

        # Get the most recent processed audio for the user
        processed = Audio.objects.filter(user=user).order_by('-uploaded_at').first()

        if not processed or not processed.processed_audio:
            return Response({"error": "No processed script found for this user, please try again"},
                            status=status.HTTP_404_NOT_FOUND)

        try:
            # Connect to Google Cloud
            if settings.GOOGLE_CLOUD_CREDENTIALS:
                client = storage.Client(credentials=settings.GOOGLE_CLOUD_CREDENTIALS)
            else:
                client = storage.Client()

            bucket = client.bucket(settings.GCS_BUCKET_NAME)
            blob = bucket.blob(processed.processed_audio)

            #Retry logic
            max_retries = 5
            retry_delay = 2
            
            for attempt in range(max_retries):
                if blob.exists():
                    print(f"audio File found on attempt {attempt + 1}")
                    break
                sleep(retry_delay)
            else:
                return Response(
                    {"error": "Processed audio is not yet ready. Please refresh or try again"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            # Generate a signed URL valid for 1 hour
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=3600,  # 1 hour
                method="GET",
                response_type="audio/mpeg"
            )

            # Prepare JSON response with signed URL
            response_data = {"audio_url": signed_url}

            # CORS support
            allowed_origins = [
                "http://localhost:5173",
                "https://scriptreadr-frontend.vercel.app"
                
            ]
            origin = request.headers.get("Origin")

            response = Response(response_data, status=status.HTTP_200_OK)

            if origin in allowed_origins:
                response['Access-Control-Allow-Origin'] = origin
                response['Access-Control-Allow-Credentials'] = 'true'
                response['Vary'] = 'Origin'

            return response

        except Exception as e:
            return Response({"error": "Failed to download script please refresh or try again."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        
        
        
        
        
#voice preview classes


class VoicePreviewSubcriptionStatusView(APIView):
    authentication_classes = [JWTAuthentication]
    
    def get(self, request):
        
        user = request.user

        try:
           subscription = UserSubscription.objects.get(user=user)
           if not subscription.is_active or (subscription.current_period_end and subscription.current_period_end < timezone.now()):
               return Response(
                   {"error": "You do not have an active subscription or your subscription has expired."},
                   status=status.HTTP_403_FORBIDDEN
               )
               
            #check scripts_remaining before allowing upload
           if subscription.audio_remaining <= 0:
                return Response({"error": "You need to have one or more 'audio(s) remaining' to preview voices, it will not be used."},
                        status=status.HTTP_403_FORBIDDEN)
       
        except UserSubscription.DoesNotExist: 
           return Response(
               {"error": "You do not have an active subscription."},
               status=status.HTTP_403_FORBIDDEN
           )
           
        return Response({"success": "user has subscription"},status=status.HTTP_200_OK)
        
           
class PreviewVoicesAPIView(APIView):
    def post(self, request):
        voice_id = request.data.get("voice_id") or settings.VOICE_ID
        text = request.data.get("text") 
        elevenlabs_api_key= settings.ELEVEN_LABS_API_KEY
        
        
        
        if not voice_id:
            return Response({"error": "Voice ID is required,"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
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
                    return Response({"error": "Failed to generate preview audio, please try again later.", "details": response.text}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return HttpResponse(response.content, content_type="audio/mpeg")

        except Exception as e:
            return Response({"error": 'failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
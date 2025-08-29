
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import re 
import requests
from typing import List, Dict
from utils.generic_script_parser import parse_script_generic
import docx
import fitz  # PyMuPDF
from django.conf import settings
from user.models import User, UploadedFile, ProcessedScript, UserSubscription
from rest_framework_simplejwt.authentication import JWTAuthentication
#google cloud imports
from google.cloud import storage
from google.api_core.exceptions import GoogleAPIError
from io import BytesIO
import os
import json
from .tasks import process_script_with_claude
from celery.result import AsyncResult
from celery.exceptions import CeleryError
from kombu.exceptions import OperationalError
from time import sleep
from django.utils import timezone



def extract_text_from_pdf(file):
        """
        Extract text from PDF while preserving layout, formatting, and structure.
        This method maintains:
        - Line breaks and spacing
        - Indentation based on x-coordinates
        - Relative positioning of text blocks
        NO PAGE MARKERS - they interfere with script parsing
        """
        try:
            file_bytes = file.read()
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            extracted_text = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Get text as dictionary with detailed positioning
                text_dict = page.get_text("dict")
                
                # Process text blocks to maintain layout
                blocks = []
                for block in text_dict["blocks"]:
                    if "lines" in block:  # Text block
                        block_text = ""
                        block_bbox = block["bbox"]
                        
                        for line in block["lines"]:
                            line_text = ""
                            line_bbox = line["bbox"]
                            
                            # Calculate indentation based on x-coordinate
                            # Use the leftmost x-coordinate to determine indentation level
                            x_pos = line_bbox[0]
                            indent_level = max(0, int((x_pos - 72) / 36))  # Rough indentation calculation
                            indent = "    " * indent_level  # 4 spaces per indent level
                            
                            for span in line["spans"]:
                                # Get the actual text
                                span_text = span["text"]
                                line_text += span_text
                            
                            if line_text.strip():  # Only add non-empty lines
                                block_text += indent + line_text.rstrip() + "\n"
                            else:
                                block_text += "\n"  # Preserve empty lines
                        
                        if block_text.strip():
                            blocks.append({
                                "text": block_text,
                                "bbox": block_bbox,
                                "y": block_bbox[1]  # Top y-coordinate for sorting
                            })
                
                # Sort blocks by vertical position (top to bottom)
                blocks.sort(key=lambda x: x["y"])
                
                # Add blocks to final text with proper spacing
                for i, block in enumerate(blocks):
                    extracted_text += block["text"]
                    
                    # Add spacing between blocks if there's a significant gap
                    if i < len(blocks) - 1:
                        current_bottom = block["bbox"][3]
                        next_top = blocks[i + 1]["bbox"][1]
                        gap = next_top - current_bottom
                        
                        # If there's a significant vertical gap, add extra line break
                        if gap > 20:  # Adjust this threshold as needed
                            extracted_text += "\n"
                
                # Add page break marker (not visible page number, just break indicator)
                if page_num < len(doc) - 1:  # Don't add after last page
                    extracted_text += "\n\n[PAGE_BREAK]\n\n"
            
            # doc.close()
            return extracted_text
            
        except Exception as e:
            print(e)
            return None



def extract_text_from_docx(file):
    doc = docx.Document(file)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text


default_prompt = """You are a script formatting expert. Your task is to convert raw script text into a clean format for text-to-speech processing.


CRITICAL REQUIREMENTS:
1. Convert ALL dialogue into the format "CHARACTER_NAME: dialogue text"
2. Convert ALL narration, title pages, introductory content, stage directions, and scene descriptions into "NARRATOR: description text"
3. Preserve the logical flow and sequence of the script
4. Remove any formatting artifacts, page numbers, or irrelevant text
5. Ensure each speaker line starts on a new line
6. Keep dialogue natural and readable for voice synthesis
7. Maintain character names consistently throughout
8. DO NOT:
   - Add any introductory or closing statements
   - Ask questions
   - Add "Here is your output" or any explantion
   - Reflect on the task
   - Say anything outside the formatted result
   - Comment when no script is provided
   - Ask for clarification
   - Say anything like “Here is the formatted script”
   - Reflect or comment on the input
   - Ask any questions
   
If no input is provided, acknowledge nothing. Say absolutely nothing.
example: Since no script was provided after "", I will remain silent as per the instructions to not respond when no input is given, do not say anything like this,


INPUT: Raw script text that may contain various formatting
OUTPUT: Clean script in "SPEAKER: text" format only

Example input:
    JOHN
    (excited)
    Hello there! How are you?
    
    MARY looks at him suspiciously.
    
    MARY
    I'm fine, thanks.

Example output:
NARRATOR: JOHN speaks excitedly.
JOHN: Hello there! How are you?
NARRATOR: MARY looks at him suspiciously.
MARY: I'm fine, thanks.

Process the following script chunk:"""



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
           if subscription.scripts_remaining <= 0:
                return Response({"error": "You have reached your script upload limit, you can buy another subscription to reset."},
                        status=status.HTTP_403_FORBIDDEN)
       
        except UserSubscription.DoesNotExist: 
           return Response(
               {"error": "You do not have an active subscription."},
               status=status.HTTP_403_FORBIDDEN
           )
           
        return Response({"success": "user has subscription"},status=status.HTTP_200_OK)
        
        
class FileUploadView(APIView):
    authentication_classes = [JWTAuthentication]
    parser_classes = [MultiPartParser, FormParser]


    def post(self, request):
       
        user = request.user
        
       #check if user has an active subscription
        subscription = UserSubscription.objects.get(user=user)
       
        #decrement scripts remaining by 1
        subscription.scripts_remaining -=1
        subscription.save()    
        
        uploaded_file = request.FILES.get('file')
        
        if not uploaded_file:
            subscription.scripts_remaining +=1
            subscription.save()
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        
        file_size_bytes = uploaded_file.size
        file_size_kb = file_size_bytes / 1024
        
        max_file_size = 2048;
        
        if file_size_kb > max_file_size:
            subscription.scripts_remaining +=1
            subscription.save()
            return Response({"error": "File is too large. Max allowed is 2MB."}, status=status.HTTP_400_BAD_REQUEST)
            
        

        file_name = uploaded_file.name.lower()
        # mime_type = uploaded_file.content_type
        
        try:
            #upload to google cloude
            if settings.GOOGLE_CLOUD_CREDENTIALS:
                client = storage.Client(credentials=settings.GOOGLE_CLOUD_CREDENTIALS)
            else:
                client = storage.Client()
            bucket = client.bucket(settings.GCS_BUCKET_NAME)
            blob = bucket.blob(f"uploads/{file_name}")
            
            #upload the file
            blob.upload_from_file(uploaded_file.file, content_type=uploaded_file.content_type)
        
            #save file info to database
            UploadedFile.objects.create(
                user=user,
                file_path=f"uploads/{file_name}" 
            )
        
        except GoogleAPIError as e:
            #add back the script count if upload to google cloud fails
            subscription.scripts_remaining +=1
            subscription.save()
            return Response({"error": "Google Cloud error, please try again later"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            subscription.scripts_remaining +=1
            subscription.save()
            print({e})
            return Response({"error": "Could not upload file to google cloud, please try again later"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # mode = request.data.get('mode', 'screenplay') #Default to 'screenplay'
    

       #Get file back from google cloud
        user_file = UploadedFile.objects.filter(user=user).order_by('-uploaded_at').first()
        
        if not user_file:
            subscription.scripts_remaining +=1
            subscription.save()
            return Response({'error': 'No file found, please try again'}, status=400)
        
        file_path = user_file.file_path   
       
        try:
            if settings.GOOGLE_CLOUD_CREDENTIALS:
                client = storage.Client(credentials=settings.GOOGLE_CLOUD_CREDENTIALS)

            else:
                client = storage.Client() 
            bucket = client.bucket(settings.GCS_BUCKET_NAME)
            blob = bucket.blob(file_path)
            
            file_bytes = blob.download_as_bytes()
            file_stream = BytesIO(file_bytes)
            
        except Exception as e:
            return Response({"error": "Could not get file from google cloude, please try again"}, status=400)

        
        # Extract text based on MIME type or file extension
        try:
            file_name = os.path.basename(file_path)
            split_result = os.path.splitext(file_name)
            file_name_without_extension = split_result[0]
            extension = split_result[1]
            
            if extension == '.pdf':
                file_text = extract_text_from_pdf(file_stream)
            elif extension == '.docx':
                file_text = extract_text_from_docx(file_stream)
            elif extension == '.txt':
                file_text = file_stream.read().decode('utf-8')

            else:
                subscription.scripts_remaining +=1
                subscription.save()
                return Response({"error": "Unsupported file format."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            subscription.scripts_remaining +=1
            subscription.save()
            subscription.refresh_from_db()
            return Response({"error": "Error processing file"}, status=status.HTTP_400_BAD_REQUEST)
        
        
        # #use the chunk function
        # chunks = chunk_script_text(file_text)
        try:
            task = process_script_with_claude.delay(default_prompt, file_text, user.email)
        except (CeleryError, OperationalError) as e:
            return Response({"error": "Background Processing Service is currently unavailable please try again later."},status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"task_id": task.id}, status=200)
        
            
# class TaskStatusView(APIView): 
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
    
    
class CancelCeleryTaskAPIView(APIView):
    def post(self, request):
        task_id = request.data.get("task_id")
        if not task_id:
            return Response({"detail": "Task ID is required"}, status=400)
        
        result = AsyncResult(task_id)
        result.revoke(terminate=True, signal='SIGTERM')
        
        return Response({"detail": "Task revoked"})
    
    
class ProcessedScriptView(APIView):
    authentication_classes = [JWTAuthentication]
    
    def get(self, request):
        user = request.user
        
        #get the most recent processed script for the user
        processed = ProcessedScript.objects.filter(user=user).order_by('-uploaded_at').first()
        
        
        if not processed or not processed.processed_script:
            return Response({"error": "No processed script found for this user."}, status=status.HTTP_404_NOT_FOUND)

        try:
            #connect to Google Cloud and download the file content
            if settings.GOOGLE_CLOUD_CREDENTIALS:
                client = storage.Client(credentials=settings.GOOGLE_CLOUD_CREDENTIALS)

            else:
                client = storage.Client()
                
            bucket = client.bucket(settings.GCS_BUCKET_NAME)
            blob = bucket.blob(processed.processed_script)
            
            
             
            
            # #retry logic to make sure the file is ready before sending a reponse
            max_retries = 5
            retry_delay = 2 
            
            for attempt in range(max_retries):
                if blob.exists():
                    print(f"got script on {attempt + 1}")
                    break
                sleep(retry_delay)
            else:
                return Response({"error": "File is not yet ready on the server. Please try again"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            
            file_content = blob.download_as_text()
            
            return Response(json.loads(file_content), status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Failed to fetch script: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
        
class UpdateSpeakerView(APIView):
    def post(self, request):
        text = request.data.get('text')
        mode = request.data.get('format', 'screenplay')
        
        if not text:
            return Response({"error": "Script text is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # choose parsing function base on format
        # if mode == 'screenplay':
        #     dialogues = parse_script_screenplay(text)
        # else:
        #     dialogues = parse_script_generic(text)
        dialogues = parse_script_generic(text)    
        #extract unique speaker names
        unique_speakers = set()
    
        for dialogue in dialogues:
            speaker = dialogue.get('speaker')
            if speaker:
                unique_speakers.add(speaker)
        speakers = list(unique_speakers)
        
        return Response({"speakers": speakers}, status=status.HTTP_200_OK)
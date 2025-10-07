import logging
from celery import shared_task
import re
from .utils import call_claude_api, chunk_script_text
from utils.generic_script_parser import parse_script_generic
from django.db import close_old_connections
from google.cloud import storage
from django.conf import settings
from datetime import datetime
import json
from user.models import User, ProcessedScript, UserSubscription
from django.core.exceptions import ObjectDoesNotExist
from google.api_core.exceptions import GoogleAPIError
import random
import time


from llama_index.core.schema import Document
from llama_index.core.node_parser import SentenceSplitter

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def process_script_with_claude(self, default_prompt, file_text, file_name, user_email):
    
    uploaded_file_name = file_name
    
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

     #extract document using lamaIndex Document class
    document = Document(text=file_text)
        
    #split the sentences using sentence splitter
    splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
        
    #get back the sentence based chunks
    nodes = splitter.get_nodes_from_documents([document])
    
    total = len(nodes)
    formatted_chunks = []
    
    for i, node in enumerate(nodes):
        chunk = node.text.strip()
        
        #skip empty chunks
        if not chunk:
            continue
        
        
        #claude call logic with retry on 'no response'
        
        for attempt in range(1, 4): 
            try:
                result = call_claude_api(default_prompt, chunk)
                if result is None or "error, no response from claude" in result.lower():
                    
                    #claude gave no response, repare to retry
                    wait_time = 5 * attempt + random.uniform(0, 1)
                    logger.warning(f"claude did not respond on attempt {attempt}")
                    time.sleep(wait_time)
                    continue
                else:
                    #successful response
                    formatted_chunks.append(result.strip())
                    break
            except Exception as e:
                wait_time = 5 * attempt + random.uniform(0, 1)
                logger.warning(f"Claude Api error on attempt {attempt} for chunk")
                time.sleep(wait_time)
                continue
        else:
            #all attempts failed, append last know result or placeholder
            error_message = f"[Error: No response from Claude after 3 attempts on chunk {i+1}]"
            logger.error(error_message)
            subscription.scripts_remaining +=1
            subscription.save()
            return {
                "status": "failed",
                "error": "Our external AI formatter returned an error, please try again."
            }
            
        
        #report real time progress
        close_old_connections()
        self.update_state(
        state='PROGRESS',
        meta={'current': i + 1, 'total': total, 'percent': int((i + 1) / total * 100)}
        )

    formatted_script = "\n\n".join(formatted_chunks)
    # Remove [PAGE_BREAK] markers from final output
    formatted_script = re.sub(r'\[PAGE_BREAK\]', '', formatted_script)

    print("this is the AI text", formatted_script)
    

    # try:
    #     dialogues = json.loads(formatted_script)
    # except json.JSONDecodeError as e:
    #     close_old_connections()
    #     subscription.scripts_remaining +=1
    #     subscription.save()
    #     return {
    #         "status": "failed",
    #         "error": f"Invalid JSON returned by AI: {str(e)}"
    #     }
     

    dialogues = parse_script_generic(formatted_script)
    
       
    if not dialogues:
        close_old_connections()
        subscription.scripts_remaining +=1
        subscription.save()
        return {
                "status": "failed",
                "error": "No dialogues found please upload your script again"
        }    
        
        
    #   #convert json file back into a plain text file
    # plain_script_text = "\n".join(f"{d['speaker']}: {d['dialogue']}" for d in dialogues)
  
      #Extract unique speakers with gender      
    unique_speakers = {}
      
    for entry in dialogues:
          speaker = entry.get("speaker")
          gender = entry.get("gender", "unknown")
          if speaker and speaker not in unique_speakers:
              unique_speakers[speaker] = gender

    speakers = [{"speaker": s, "gender": g} for s, g in unique_speakers.items()]
        
    # unique_speakers = set()
    
    #  # Step 2: Loop through each entry in the dialogues list
    # for entry in dialogues:
    #     # Step 3: Get the speaker from the entry and add it to the set
    #     speaker = entry["speaker"]
    #     unique_speakers.add(speaker)

    # # Step 4: Convert the set to a list
    # speakers = list(unique_speakers)

    close_old_connections()
    final_result =  {
            "script": formatted_script, #plain_script_text,
            "dialogue": dialogues,
            "speakers": speakers
        }

    #upload to Google Cloud Storage
    try:
        if settings.GOOGLE_CLOUD_CREDENTIALS:
            client = storage.Client(credentials=settings.GOOGLE_CLOUD_CREDENTIALS)
        else:
            client = storage.Client()
        bucket = client.bucket(settings.GCS_BUCKET_NAME)
        filename = f"processed_script/{user.email}_processed_script.json"
        blob = bucket.blob(filename)
    
        blob.upload_from_string(
            data=json.dumps(final_result),
            content_type="application/json"
            )
    except GoogleAPIError as e:
        subscription.scripts_remaining +=1
        subscription.save()
        return {
            "status": "failed",
            "error": "Could not upload you file to google cloud, please try again later."}
    
    close_old_connections()
    try:
        #Update or create the UploadedFile record (depends on your lagic)
        processed_script = ProcessedScript.objects.filter(user=user).order_by('-uploaded_at').first()
    
        if  processed_script:
            processed_script.processed_script = filename
            processed_script.file_name = uploaded_file_name
            processed_script.save()
        else:
            ProcessedScript.objects.create(
                user=user,
                processed_script=filename,
                file_name=uploaded_file_name 
            )
    except:
        return {
            "status": "failed",
            "error": "Could not create your upload file record, please try again."
        }
        
        
    close_old_connections()
    
    return {"status": "success"}
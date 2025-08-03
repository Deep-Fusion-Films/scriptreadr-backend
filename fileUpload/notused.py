# formatted_chunks = []
        # total_chunks = len(chunks)
        # for i, chunk in enumerate(chunks):
        #    formatted_chunk = call_claude_api.delay(default_prompt, chunk)
        #    formatted_chunks.append(formatted_chunk)
        #    print(f"the chunks:{formatted_chunk}")

           
        # formatted_script = "\n\n".join(formatted_chunks)
           
        # # Remove [PAGE_BREAK] markers from final output
        # formatted_script = re.sub(r'\[PAGE_BREAK\]', '', formatted_script)
           
           
         #parse formatted scripts using generic script parser   
        # dialogues = parse_script_generic(formatted_script)
        
        # print(dialogues)
            

         
        # Parse script to extract speakers
        # if mode == 'screenplay':
        #     dialogues = parse_script_screenplay(file_text)
        # else:
            # dialogues = parse_script_generic(file_text)
            
        # if not dialogues:
        #     return Response({
        #         "error": f"No dialogues found in {mode} format. Please check your script formatting or try a different format."
        #     }, status=status.HTTP_400_BAD_REQUEST)    
        
        # # Step 1: Create an empty set to store unique speaker names
        # unique_speakers = set()

        # # Step 2: Loop through each entry in the dialogues list
        # for entry in dialogues:
        #     # Step 3: Get the speaker from the entry and add it to the set
        #     speaker = entry["speaker"]
        #     unique_speakers.add(speaker)

        # # Step 4: Convert the set to a list
        # speakers = list(unique_speakers)
        # print(speakers)

        # return Response({
        #     "script": formatted_script,
        #     "dialogue": dialogues,
        #     "original_filename": uploaded_file.name,
        #     "speakers": speakers
        # }, status=status.HTTP_200_OK)









#old tasks
# import logging
# from celery import shared_task
# import re
# from .utils import call_claude_api, chunk_script_text
# from utils.generic_script_parser import parse_script_generic
# from django.db import close_old_connections
# from google.cloud import storage
# from django.conf import settings
# from datetime import datetime
# import json
# from user.models import User, ProcessedScript
# from django.core.exceptions import ObjectDoesNotExist
# from google.api_core.exceptions import GoogleAPIError

# from llama_index.core.schema import Document
# from llama_index.core.node_parser import SentenceSplitter

# logger = logging.getLogger(__name__)

# @shared_task(bind=True)
# def process_script_with_claude(self, default_prompt, file_text, user_email):
    
#     close_old_connections()
    
#     try:
#         user = User.objects.get(email=user_email)
#     except ObjectDoesNotExist:
#         return {"error": "User not found"}
    
#      #extract document using lamaIndex Document class
#     document = Document(text=file_text)
        
#     #split the sentences using sentence splitter
#     splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
        
#     #get back the sentence based chunks
#     nodes = splitter.get_nodes_from_documents([document])
    
#     total = len(nodes)
#     formatted_chunks = []
    
#     for i, node in enumerate(nodes):
#         chunk = node.text.strip()
        
#         #skip empty chunks
#         if not chunk:
#             continue 
#         try:
#             result = call_claude_api(default_prompt, chunk)
#             if result is None:
#                 result = "[Error: No response from Claude]"
#         except Exception as e:
#             result = f"[Error: Claude failed on chunk {i+1}]"
            
#         formatted_chunks.append(result)
        
#         #report real time progress
#         close_old_connections()
#         self.update_state(
#         state='PROGRESS',
#         meta={'current': i + 1, 'total': total, 'percent': int((i + 1) / total * 100)}
#         )

#     formatted_script = "\n\n".join(formatted_chunks)
#     # Remove [PAGE_BREAK] markers from final output
#     formatted_script = re.sub(r'\[PAGE_BREAK\]', '', formatted_script)
    
#     dialogues = parse_script_generic(formatted_script)
    
#     if not dialogues:
#         close_old_connections()
#         return {
#                 "error": "No dialogues found please upload your script again"
#         }    
        
#     unique_speakers = set()
    
#      # Step 2: Loop through each entry in the dialogues list
#     for entry in dialogues:
#         # Step 3: Get the speaker from the entry and add it to the set
#         speaker = entry["speaker"]
#         unique_speakers.add(speaker)

#     # Step 4: Convert the set to a list
#     speakers = list(unique_speakers)

#     close_old_connections()
#     final_result =  {
#             "script": formatted_script,
#             "dialogue": dialogues,
#             "speakers": speakers
#         }

#     #upload to Google Cloud Storage
#     try:
#         if settings.GOOGLE_CLOUD_CREDENTIALS:
#             client = storage.Client(credentials=settings.GOOGLE_CLOUD_CREDENTIALS)
#         else:
#             client = storage.Client()
#         bucket = client.bucket(settings.GCS_BUCKET_NAME)
#         filename = f"processed_script/{user.email}_processed_script.json"
#         blob = bucket.blob(filename)
    
#         blob.upload_from_string(
#             data=json.dumps(final_result),
#             content_type="application/json"
#             )
#     except GoogleAPIError as e:
#         return {"error": f"Google Cloud error: {str(e)}"}
    
#     close_old_connections()
#     #Update or create the UploadedFile record (depends on your lagic)
#     processed_script = ProcessedScript.objects.filter(user=user).order_by('-uploaded_at').first()
    
#     if  processed_script:
#         processed_script.processed_script = filename
#         processed_script.save()
#     else:
#         ProcessedScript.objects.create(
#                 user=user,
#                 processed_script=filename 
#             )
        
        
#     close_old_connections()
    
#     return {"status": "success"}
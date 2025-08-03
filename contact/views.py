
# Create your views here.
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
from user.models import User, UploadedFile, ProcessedScript
from rest_framework_simplejwt.authentication import JWTAuthentication
#google cloud imports
from google.cloud import storage
from google.api_core.exceptions import GoogleAPIError
from io import BytesIO
from rest_framework_simplejwt.authentication import JWTAuthentication
import os
import json
from celery.result import AsyncResult
from time import sleep
from contact.utils import send_contact_email



class ContactAPIview(APIView):
    authentication_classes = [JWTAuthentication]
    
    def post(self, request):
        user = request.user
        data = request.data
        
        required_fields = ['fullname', 'email', 'subject', 'message']

        for field in required_fields:
            value = data.get(field, '').strip()
        if value == '':
            return Response({'detail': 'Fields cannot be empty'}, status=400)
        
        success, error_message = send_contact_email(
            from_name=data.get('fullname'),
            from_email=data.get('email'),
            subject=data.get('subject'),
            message=data.get('message')
        )
        
        if success:
            return Response({'detail': 'Message sent successfully, we will get back to you '})
        else:
            return Response({'detail': 'Message could not be sent at this time. Please try again later'})
        
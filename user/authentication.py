import jwt
import datetime
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.response import Response
from user.models import User
from django.conf import settings


access_secret=settings.TOKEN_ACCESS_SECRET
refresh_secret=settings.TOKEN_REFRESH_SECRET

class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        
        if auth and len(auth) == 2:
            token = auth[1].decode('utf-8')
            id = decode_access_token(token)

            user = User.objects.get(pk=id)
            return (user, None)
            
        raise exceptions. AuthenticationFailed('unauthenticated')
    

def create_access_token(id):
    expiration = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    issued_at = datetime.datetime.utcnow()
    
    return jwt.encode({
        'user_id': id,
        'exp': int(expiration.timestamp()),
        'iat': int(issued_at.timestamp())
    }, access_secret, algorithm='HS256')

def decode_access_token(token):
    try:
        payload = jwt.decode(token, access_secret, algorithms='HS256')
        return payload['user_id']
    except Exception as e:
        print(e)
        raise exceptions.AuthenticationFailed('unauthenticated')

def create_refresh_token(id):
    expiration = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
    issued_at = datetime.datetime.now(datetime.timezone.utc)
    
    return jwt.encode({
        'user_id': id,
        'exp': int(expiration.timestamp()),
        'iat': int(issued_at.timestamp())
    }, refresh_secret, algorithm='HS256')


def decode_refresh_token(token):
    try:
        payload = jwt.decode(token, refresh_secret, algorithms='HS256')
        return payload['user_id']
    except Exception as e:
        print(e)
        raise exceptions.AuthenticationFailed('unauthenticated')

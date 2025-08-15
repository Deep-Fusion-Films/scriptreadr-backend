from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import get_authorization_header
from rest_framework import exceptions,status
from user.serializers import UserSerializer
from user.models import User, UserToken, Reset, UserSubscription
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.mail import send_mail
from datetime import timedelta
from django.utils import timezone
import random
import string
from user.authentication import create_access_token, create_refresh_token, decode_refresh_token
from user.utils import authenticate_google_user, send_reset_email
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed

from rest_framework.throttling import UserRateThrottle
from rest_framework.exceptions import Throttled

# Create your views here.

#register users
class RegisterAPIView(APIView):
    def post(self, request):
        data = request.data
        
        if not data.get("first_name", "").strip():
            return Response({'detail': 'No empty field(s)'}, status=status.HTTP_400_BAD_REQUEST)
        if not data.get("last_name", "").strip():
            return Response({'detail': 'No empty field(s)'}, status=status.HTTP_400_BAD_REQUEST)
        if not data.get("email", "").strip():
            return Response({'detail': 'No empty field(s)'}, status=status.HTTP_400_BAD_REQUEST)
        if not data.get("password", "").strip():
            return Response({'detail': 'No empty field(s)'}, status=status.HTTP_400_BAD_REQUEST)
        if not data.get("confirm_password", "").strip():
            return Response({'detail': 'No empty field(s)'}, status=status.HTTP_400_BAD_REQUEST)
       
        #check if passwords match
        if data['password'] != data['confirm_password']:
            return Response({
                "detail": "Passwords do not match."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        #check if user already exists using entered email    
        if User.objects.filter(email=data.get('email')).exists():
            return Response({'detail': 'Email is already in use'}, status=status.HTTP_400_BAD_REQUEST)
                    
        serializer = UserSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
           
           
#login throttle, prevents brute force attack on route
class LoginRateThrottle(UserRateThrottle):
    rate = '5/min'
    
    def get_cache_key(self, request, view):
        ident = request.data.get('email', '').lower().strip()
        if not ident:
            ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }
        
    def wait(self):
        #returns the remaining time in seconds
        return super().wait()

    def allow_request(self, request, view):
        allowed = super().allow_request(request, view)
        if not allowed:
            raise Throttled(detail=f'Too many login attempts. Please wait {int(self.wait())} seconds before trying again.')
        return allowed
    
#login users
class LoginAPIView(APIView):
    throttle_classes = [LoginRateThrottle]
    def post(self, request):
        email = request.data['email']
        password = request.data['password']
         
         
        if not email.strip():
            return Response({'detail': 'No empty field(s)'}, status=status.HTTP_400_BAD_REQUEST)
        if not password.strip():
            return Response({'detail': 'No empty field(s)'}, status=status.HTTP_400_BAD_REQUEST)
       
        try:
           user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response ({'detail': 'User with this email does not exist'}, status=status.HTTP_404_NOT_FOUND)
       
        user = authenticate(request, username=email, password=password)
                
        if user is None:
            raise exceptions.AuthenticationFailed('Incorrect Password')
        
        
        
        if user.email and user.email.lower().endswith('@deepfusionfilms.com'):
            subscription, created = UserSubscription.objects.get_or_create(user=user)
        
            subscription.current_plan = 'studio'
            subscription.is_active = True
            subscription.subscribed_at = timezone.now()
            subscription.scripts_remaining = 25  # or whatever unlimited means
            subscription.audio_remaining = 25
            subscription.current_period_end = timezone.now() + timedelta(days=365)  # 1 year validity
        
            subscription.save()
        
        
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        response = Response()
        
        # locals
        # secure=False, samesite='Lax'
        
        # production
        # secure=True, samesite='None'
        
        response.set_cookie(key='refresh_token', value=refresh_token, httponly=True, secure=True, samesite='None', expires=timezone.now() + timedelta(days=7))
        response.data = {
            'token': access_token
        }
        
        return response

#get single user
class UserAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    
    def get(self, request):
        return Response(UserSerializer(request.user).data)
    
    def patch(self, request):
        user = request.user
        
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.erros, statu=400)
    


#refresh access token with refresh token
class RefreshAPIView(APIView):
    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        
        print(refresh_token)
        if not refresh_token:
            raise AuthenticationFailed('No refresh token provided')

        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
            return Response({'token': access_token})
        except Exception as e:
            raise AuthenticationFailed('Invalid refresh token')
        
        # return Response({
        #     'token': access_token
        # })
        
 #logout user       
class LogoutAPIView(APIView):
    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        
        if not refresh_token:
            raise AuthenticationFailed('No refresh token provided')
        
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()  # blacklist the refresh token
        except TokenError:
            raise AuthenticationFailed('Invalid or expired token')

        response = Response({'message': 'Logged out successfully'})
        response.delete_cookie('refresh_token')
        return response

        # UserToken.objects.filter(token=refresh_token).delete()
        
        # response = Response()
        # response.delete_cookie(key='refresh_token')
        # response.data = {
        #     'message': 'success'
        # }
        
        # return response
    
#forgot password
@method_decorator(csrf_exempt, name='dispatch')
class ForgotAPIView(APIView):
    def post(self, request):
        email = request.data['email']
        
        if isinstance(email, list):
            email = email[0].strip()
        print(email)
        
        if not email:
            return Response({'detail': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.filter(email=email).first()
        
        if user is None:
            raise exceptions.AuthenticationFailed('User does not exist')
        
        token = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))

        Reset.objects.create(
            email=email,
            token=token
        )
        
        try:
            send_reset_email(email, token)
        except Exception as e:
            return Response({'detail': 'could not send email, please try again later.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'message': 'An email has been sent to your registered email'
        })
        
#reset user password
class ResetAPIView(APIView):
    def post(self, request):
        data = request.data
        
        if not data.get("new_password", "").strip():
            return Response({'detail': 'No empty field(s)'}, status=status.HTTP_400_BAD_REQUEST)
        if not data.get("confirm_password", "").strip():
            return Response({'detail': 'No empty field(s)'}, status=status.HTTP_400_BAD_REQUEST)
        
        if data['new_password'] != data['confirm_password']:
            raise exceptions.APIException('Passwords do not match')
    
        
        reset_password = Reset.objects.filter(token=data['token']).first()
        
        print(data['token'])
        if not reset_password:
            raise exceptions.APIException('Invalid link!')
        user = User.objects.filter(email=reset_password.email).first()
        
        if not user:
            raise exceptions.APIException('User not found')
        
        user.set_password(data['new_password'])
        user.save()
        
        return Response({
            'message': 'You have successfully reset your password'
        })

#register throttle, stops constant registration from the same IP address after 3 tries withing 1 minute.
class RegistrationRateThrottle(UserRateThrottle):
    rate = '3/min' 
    
#google register view
class GoogleRegisterAPIView(APIView):
    def post(self, request):
        code = request.data.get('code')
        if not code:
            return Response({'detail': 'Could not get authorization from google'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_info = authenticate_google_user(code)
        except Exception as e:
            return Response({'detail': 'Google authentication failed, please try again.'}, status=status.HTTP_400_BAD_REQUEST)

        email = user_info.get('email')
        first_name = user_info.get('given_name')
        last_name = user_info.get('family_name')

        if not email:
            return Response({'detail': 'Google account did not return an email'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({'detail': 'Email is already in use'}, status=status.HTTP_400_BAD_REQUEST)

        user_data = {
            'email': email,
            'first_name': first_name,
            'last_name': last_name
        }

        serializer = UserSerializer(data=user_data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
#google signin view
class GoogleSigninAPIView(APIView):
    def post (self, request):
        if 'code' in request.data.keys():
            code = request.data['code']
            id = authenticate_google_user(code)
        
            user = User.objects.filter(email=id['email']).first()
        
            if user is None:
                raise exceptions.AuthenticationFailed('User does not exist')
            
            
            if user.email and user.email.lower().endswith('@deepfusionfilms.com'):
                subscription, created = UserSubscription.objects.get_or_create(user=user)
        
                subscription.current_plan = 'studio'
                subscription.is_active = True
                subscription.subscribed_at = timezone.now()
                subscription.scripts_remaining = 25  # or whatever unlimited means
                subscription.audio_remaining = 25
                subscription.current_period_end = timezone.now() + timedelta(days=365)  # 1 year validity
        
                subscription.save()
        
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
        
            response = Response()
          
        
            response.set_cookie(key='refresh_token', value=refresh_token, httponly=True, secure=True, samesite='None', expires=timezone.now() + timedelta(days=7))
            response.data = {
                'token': access_token
            }
        
            return response

        return Response({'error': 'Google login failed'}, status=status.HTTP_400_BAD_REQUEST)
            

class DeleteUserAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    
    def delete(self, request):
        user = request.user
        user.delete()
        return Response({"detail": "User account deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        
    

from django.urls import path
from user.views import RegisterAPIView, LoginAPIView, UserAPIView, RefreshAPIView, LogoutAPIView, ForgotAPIView, ResetAPIView, GoogleRegisterAPIView, GoogleSigninAPIView, DeleteUserAPIView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns =[
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('users/', UserAPIView.as_view(), name='user'),
    path('refresh/', RefreshAPIView.as_view(), name='refresh'),
    path('logout/', LogoutAPIView.as_view(), name='logout' ),
    path('forgot/', ForgotAPIView.as_view(), name='forgot' ),
    path('reset/', ResetAPIView.as_view(), name='reset'),
    path('googleregister/', GoogleRegisterAPIView.as_view(), name='googleregister'),
    path('googlesignin/', GoogleSigninAPIView.as_view(), name='googlesignin'),
    path('delete_user/', DeleteUserAPIView.as_view(), name='delete_user')
]

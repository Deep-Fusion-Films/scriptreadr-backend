
from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class User(AbstractUser):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=255)
    username = None
    
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)  # ← add this line

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
class UserToken(models.Model):
    user_id = models.IntegerField()
    token = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField()
 
class UserSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    current_plan = models.CharField(max_length=20, choices=[
        ('one_off', 'One Off'),
        ('starter', 'Starter'),
        ('pro', 'Pro'),
        ('studio', 'Studio'),
    ], blank=True, null=True)
    is_active = models.BooleanField(default=False)
    subscribed_at = models.DateTimeField(blank=True, null=True)
    scripts_remaining = models.IntegerField(default=0)
    audio_remaining = models.IntegerField(default=0)
    current_period_end = models.DateTimeField(blank=True, null=True)

class UploadedFile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file_path = models.CharField(max_length=500)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
class ProcessedScript(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    processed_script = models.CharField(max_length=500)
    file_name = models.CharField(max_length=255, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
class Audio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    processed_audio = models.CharField(max_length=500)
    audio_name = models.CharField(max_length=255, null=True, blank=True) 
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
class Reset(models.Model):
    email = models.CharField(max_length=255)
    token = models.CharField(max_length=255, unique=True)

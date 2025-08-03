from django.urls import path
from contact.views import ContactAPIview



urlpatterns = [
    path('contact_us/', ContactAPIview.as_view(), name='contact_us'),
]
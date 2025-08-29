from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/task/", consumers.task_status_consumer.as_asgi()),
]
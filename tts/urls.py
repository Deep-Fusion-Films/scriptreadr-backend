from django.urls import path

from tts.views import Tts, PreviewVoicesAPIView, TaskStatusView, ProcessedAudioView, CancelAudioTaskAPIView, SubscriptionStatusView


urlpatterns = [
    path('tts/', Tts.as_view(), name='tts'),
    path('preview/', PreviewVoicesAPIView.as_view(), name='preview_voices'),
    path('task-status/<str:task_id>/', TaskStatusView.as_view(), name='task_status'),
    path('processed_audio/', ProcessedAudioView.as_view(), name='processed_audio'),
    path('cancel_audio_task/', CancelAudioTaskAPIView.as_view(), name='cancel_audio_task'),
    path('subscription_audio/', SubscriptionStatusView.as_view(), name='subscription_audio')
]
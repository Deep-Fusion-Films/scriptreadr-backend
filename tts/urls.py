from django.urls import path

from tts.views import Tts,SingleAudioDeleteView, SingleAudioView, UserAudiosView, PreviewVoicesAPIView, TaskStatusView, ProcessedAudioView, CancelAudioTaskAPIView, SubscriptionStatusView, VoicePreviewSubcriptionStatusView 


urlpatterns = [
    path('tts/', Tts.as_view(), name='tts'),
    path('preview/', PreviewVoicesAPIView.as_view(), name='preview_voices'),
    path('task-status/<str:task_id>/', TaskStatusView.as_view(), name='task_status'),
    path('single_audio/', SingleAudioView.as_view(), name='single_audio'),
    path('delete_single_audio/', SingleAudioDeleteView.as_view(), name='delete_single_audio'),
    path('processed_audio/', ProcessedAudioView.as_view(), name='processed_audio'),
    path('user_audios/', UserAudiosView.as_view(), name="user_audios"),
    path('cancel_audio_task/', CancelAudioTaskAPIView.as_view(), name='cancel_audio_task'),
    path('subscription_audio/', SubscriptionStatusView.as_view(), name='subscription_audio'),
    path('subscription_preview/', VoicePreviewSubcriptionStatusView.as_view(), name='subscription_preview')
]
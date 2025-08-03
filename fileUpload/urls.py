from django.urls import path

from fileUpload.views import FileUploadView, UpdateSpeakerView, TaskStatusView, ProcessedScriptView, CancelCeleryTaskAPIView, SubscriptionStatusView


urlpatterns = [
    path('upload/', FileUploadView.as_view(), name='file_upload'),
    path('update/', UpdateSpeakerView.as_view(), name='update_speaker'),
    path('task-status/<str:task_id>/', TaskStatusView.as_view(), name='task_status'),
    path('script/', ProcessedScriptView.as_view(), name='script'),
    path('cancel_task/', CancelCeleryTaskAPIView.as_view(), name='cancel_task'),
    path('subscription_status/', SubscriptionStatusView.as_view(), name='Subscription_status')
]
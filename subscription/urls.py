from django.urls import path
from subscription.views import CreateOne_offCheckoutSessionView, CreateStarterCheckoutSessionView, CreateProCheckoutSessionView, CreateStudioCheckoutSessionView, StripeWebhookView, CancelSubscriptionView, CurrentSubscriptionApiView


urlpatterns =[
    path('one_off/', CreateOne_offCheckoutSessionView.as_view(), name='one_off'),
    path('starter/', CreateStarterCheckoutSessionView.as_view(), name='starter'),
    path('pro/', CreateProCheckoutSessionView.as_view(), name='pro'),
    path('studio/', CreateStudioCheckoutSessionView.as_view(), name='studio'),
    path('stripe/', StripeWebhookView.as_view(), name="stripe"),
    path('current_subscription/', CurrentSubscriptionApiView.as_view(), name='current_subscription'), 
    path('cancel_subscription/', CancelSubscriptionView.as_view(), name='cancel_subscription')
]

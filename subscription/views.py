import stripe
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import get_authorization_header
from rest_framework import exceptions,status
from user.serializers import UserSerializer
from user.models import User, UserSubscription
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.mail import send_mail
from datetime import datetime, timezone as dt_timezone
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
from django.conf import settings



# Create your views here.

stripe.api_key = settings.STRIPE_SECRETE_KEY

class CreateOne_offCheckoutSessionView(APIView):
        authentication_classes = [JWTAuthentication]
        
        def post(self, request):
            user = request.user
            try:
                if not user.stripe_customer_id:
                    customer = stripe.Customer.create(email=user.email)
                    user.stripe_customer_id = customer.id
                    user.save()
                else:
                    customer = stripe.Customer.retrieve(user.stripe_customer_id)
                    
                #create checkout session
                session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    mode='payment',
                    customer=customer.id,
                    line_items=[{
                        'price': settings.STRIPE_ONE_OFF_PRICE_ID,
                        'quantity': 1,
                    }],
                    success_url=f"{settings.STRIPE_REDIRECT_LINK}/success",
                    cancel_url=f"{settings.STRIPE_REDIRECT_LINK}/cancel"                
                )
            
                return Response({'sessionId': session.id})
            except Exception as e:
                return Response({'error': str(e)}, status=400)



class CreateStarterCheckoutSessionView(APIView):
        authentication_classes = [JWTAuthentication]
        
        def post(self, request):
            user = request.user
            try:
                if not user.stripe_customer_id:
                    customer = stripe.Customer.create(email=user.email)
                    user.stripe_customer_id = customer.id
                    user.save()
                else:
                    customer = stripe.Customer.retrieve(user.stripe_customer_id)
                    
                #create checkout session
                session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    mode='subscription',
                    customer=customer.id,
                    line_items=[{
                        'price': settings.STRIPE_STARTER_PRICE_ID,
                        'quantity': 1,
                    }],
                    success_url=f"{settings.STRIPE_REDIRECT_LINK}/success",
                    cancel_url=f"{settings.STRIPE_REDIRECT_LINK}/cancel"                
                )
            
                return Response({'sessionId': session.id})
            except Exception as e:
                return Response({'error': str(e)}, status=400)


class CreateProCheckoutSessionView(APIView):
        authentication_classes = [JWTAuthentication]
        
        def post(self, request):
            user = request.user
            try:
                if not user.stripe_customer_id:
                    customer = stripe.Customer.create(email=user.email)
                    user.stripe_customer_id = customer.id
                    user.save()
                else:
                    customer = stripe.Customer.retrieve(user.stripe_customer_id)
                    
                #create checkout session
                session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    mode='subscription',
                    customer=customer.id,
                    line_items=[{
                        'price': settings.STRIPE_PRO_PRICE_ID,
                        'quantity': 1,
                    }],
                    success_url=f"{settings.STRIPE_REDIRECT_LINK}/success",
                    cancel_url=f"{settings.STRIPE_REDIRECT_LINK}/cancel"                
                )
            
                return Response({'sessionId': session.id})
            except Exception as e:
                return Response({'error': str(e)}, status=400)



class CreateStudioCheckoutSessionView(APIView):
        authentication_classes = [JWTAuthentication]
        
        def post(self, request):
            user = request.user
            try:
                if not user.stripe_customer_id:
                    customer = stripe.Customer.create(email=user.email)
                    user.stripe_customer_id = customer.id
                    user.save()
                else:
                    customer = stripe.Customer.retrieve(user.stripe_customer_id)
                    
                #create checkout session
                session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    mode='subscription',
                    customer=customer.id,
                    line_items=[{
                        'price': settings.STRIPE_STUDIO_PRICE_ID,
                        'quantity': 1,
                    }],
                    success_url=f"{settings.STRIPE_REDIRECT_LINK}/success",
                    cancel_url=f"{settings.STRIPE_REDIRECT_LINK}/cancel"                
                )
            
                return Response({'sessionId': session.id})
            except Exception as e:
                return Response({'error': str(e)}, status=400)



class CancelSubscriptionView(APIView):
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        user = request.user
        try:
            # Get the user's active subscription
            subscriptions = stripe.Subscription.list(
                customer=user.stripe_customer_id,
                status='active',
                limit=1
            )

            if not subscriptions.data:
                return Response({"error": "No active subscription found."}, status=status.HTTP_404_NOT_FOUND)

            subscription_id = subscriptions.data[0].id

            # Cancel the subscription
            stripe.Subscription.delete(subscription_id)

            return Response({"message": "Subscription cancelled successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



class CurrentSubscriptionApiView(APIView):
    authentication_classes =[JWTAuthentication]
    
    def get(self, request):
        user = request.user
        
        try:
            user_subscription = UserSubscription.objects.get(user=user)
            data = {
                "current_plan": user_subscription.current_plan,
                "is_active": user_subscription.is_active,
                "subscribed_at": user_subscription.subscribed_at,
                "current_period_end": user_subscription.current_period_end,
                "scripts_remaining": user_subscription.scripts_remaining,
                "audio_remaining": user_subscription.audio_remaining
            }
            
            return Response(data, status=status.HTTP_200_OK)
        except UserSubscription.DoesNotExist:
            return Response ({"detail": "Not Subscribed"}, status=status.HTTP_400_BAD_REQUEST)
        
        
        




STRIPE_PRICE_ID_TO_PLAN = {
    settings.STRIPE_ONE_OFF_PRICE_ID: 'one_off',
    settings.STRIPE_STARTER_PRICE_ID: 'starter',
    settings.STRIPE_PRO_PRICE_ID: 'pro',
    settings.STRIPE_STUDIO_PRICE_ID: 'studio',
}

@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
            print("stripe signature is good")
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            print(f"webhook signature verification failed: {e}")
            return Response({"error": f"Webhook error: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        event_type = event['type']
        data = event['data']['object']

        try:
            if event_type == 'checkout.session.completed':
                customer_id = data.get('customer')

                user = User.objects.filter(stripe_customer_id=customer_id).first()
                print(user)
                if not user:
                    print(f"No user with this customer ID: {customer_id}")
                    return Response({"error": f"No user with customer_id {customer_id}"}, status=status.HTTP_404_NOT_FOUND)

                # Retrieve checkout session to get price ID
                checkout_session = stripe.checkout.Session.retrieve(
                    data['id'],
                    expand=['line_items']
                )
                price_id = checkout_session['line_items']['data'][0]['price']['id']
                plan_type = STRIPE_PRICE_ID_TO_PLAN.get(price_id)

                if not plan_type:
                    print(f"This plan type is nuknown {plan_type}")
                    return Response({"error":f"Unknown price_id: {price_id}"}, status=status.HTTP_400_BAD_REQUEST)

                subscription_id = checkout_session.get('subscription')
                period_end = None
                
                if subscription_id:
                    stripe_subscription = stripe.Subscription.retrieve(subscription_id)
                    period_end_timestamp = stripe_subscription['items']['data'][0]['current_period_end']
                    period_end = datetime.fromtimestamp(period_end_timestamp, tz=dt_timezone.utc)
                   

                # Get or create the user's subscription record
                subscription, created = UserSubscription.objects.get_or_create(user=user)
                print(f"after subscription{user}")
                
                # Update subscription fields
                subscription.current_plan = plan_type
                subscription.is_active = True
                subscription.subscribed_at = timezone.now()
                subscription.current_period_end = period_end
                
                #set scripts_remaining based on current plan
                if subscription.current_plan == 'one_off':
                    subscription.scripts_remaining = 1
                    subscription.audio_remaining = 1
                elif subscription.current_plan == 'starter':
                    subscription.scripts_remaining = 5
                    subscription.audio_remaining = 5
                elif subscription.current_plan == 'pro':
                    subscription.scripts_remaining = 10
                    subscription.audio_remaining = 10
                elif subscription.current_plan == 'studio':
                    subscription.scripts_remaining = 25
                    subscription.audio_remaining = 25
                else:
                    subscription.scripts_remaining = 0
                    subscription.audio_remaining = 0
                subscription.save()

                print(f"{plan_type} subscription activated for {user.email} valid till {period_end} with {subscription.scripts_remaining} scripts")
                
            elif event_type == 'invoice.payment_succeeded':
                customer_id = data['customer']
                stripe_subscription_id = data['subscription']
                stripe_subscription = stripe.Subscription.retrieve(stripe_subscription_id)
                period_end_timestamp = stripe_subscription['items']['data'][0]['current_period_end']
                period_end = datetime.fromtimestamp(period_end_timestamp, tz=dt_timezone.utc)
                   
                
                subscription = UserSubscription.objects.filter(user__stripe_customer_id=data['customer']).first()
                if subscription:
                    subscription.is_active = True
                    subscription.current_period_end = period_end
                    
                    #reset scripts_remaining based on current plan
                if subscription.current_plan == 'one_off':
                    subscription.scripts_remaining = 1
                    subscription.audio_remaining = 1
                elif subscription.current_plan == 'starter':
                    subscription.scripts_remaining = 5
                    subscription.audio_remaining = 5
                elif subscription.current_plan == 'pro':
                    subscription.scripts_remaining = 10
                    subscription.audio_remaining = 10
                elif subscription.current_plan == 'studio':
                    subscription.scripts_remaining = 25
                    subscription.audio_remaining = 25
                else:
                    subscription.scripts_remaining = 0
                    subscription.audio_remaining = 0
                subscription.save()
                print(f"Payment succeeded for {subscription.user.email} till {period_end} with {subscription.scripts_remaining} remaining")

            elif event_type == 'customer.subscription.deleted':
                stripe_subscription_id = data['id']
                stripe_subscription = stripe.Subscription.retrieve(stripe_subscription_id)
                period_end_timestamp = stripe_subscription['items']['data'][0]['current_period_end']
                period_end = datetime.fromtimestamp(period_end_timestamp, tz=dt_timezone.utc)
                   
                subscription = UserSubscription.objects.filter(user__stripe_customer_id=data['customer']).first()
                if subscription:
                    subscription.is_active = True
                    subscription.current_period_end = period_end
                    subscription.save()
                    print(f"Subscription canceled for {subscription.user.email}, till {period_end}")

            elif event_type == 'invoice.payment_failed':
                subscription = UserSubscription.objects.filter(user__stripe_customer_id=data['customer']).first()
                if subscription:
                    subscription.is_active = False
                    subscription.save()
                    print(f"Payment failed for {subscription.user.email}")
            else:
                print(f"Unhandled event type: {event_type}")
            return Response(status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error":f"Webhook processing error:{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


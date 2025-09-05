# tests/test_tts_subscription_views.py
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
from django.utils import timezone
from django.contrib.auth import get_user_model
from subscription.models import UserSubscription
#from audio.models import Audio  # adjust if your app name differs

User = get_user_model()


class SubscriptionStatusViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="password123")
        self.client.force_authenticate(user=self.user)

    def test_subscription_not_exists(self):
        url = reverse("subscription_status")  # your URL name
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("error", response.data)

    def test_subscription_expired(self):
        UserSubscription.objects.create(
            user=self.user,
            current_plan="starter",
            is_active=True,
            current_period_end=timezone.now() - timezone.timedelta(days=1),
            scripts_remaining=5,
            audio_remaining=5,
        )
        url = reverse("subscription_status")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("error", response.data)

    def test_subscription_audio_limit_reached(self):
        UserSubscription.objects.create(
            user=self.user,
            current_plan="starter",
            is_active=True,
            current_period_end=timezone.now() + timezone.timedelta(days=5),
            scripts_remaining=5,
            audio_remaining=0,
        )
        url = reverse("subscription_status")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("error", response.data)

    def test_subscription_active(self):
        UserSubscription.objects.create(
            user=self.user,
            current_plan="starter",
            is_active=True,
            current_period_end=timezone.now() + timezone.timedelta(days=5),
            scripts_remaining=5,
            audio_remaining=5,
        )
        url = reverse("subscription_status")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("success", response.data)


class TtsViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="password123")
        self.client.force_authenticate(user=self.user)
        self.subscription = UserSubscription.objects.create(
            user=self.user,
            current_plan="starter",
            is_active=True,
            current_period_end=timezone.now() + timezone.timedelta(days=5),
            scripts_remaining=5,
            audio_remaining=5,
        )

    @patch("requests.get")
    def test_get_voices_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "voices": [{"voice_id": "v1", "name": "Voice1"}]
        }
        mock_get.return_value = mock_response

        url = reverse("tts_get_voices")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

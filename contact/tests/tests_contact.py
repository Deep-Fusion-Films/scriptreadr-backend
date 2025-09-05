# tests/test_contact_view.py
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch
from django.contrib.auth import get_user_model

User = get_user_model()


class ContactAPIViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="password123"
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse("contact")  # replace with your URL name

    def test_post_missing_fields(self):
        data = {
            "fullname": "Test User",
            "email": "",
            "subject": "Hello",
            "message": "Hi there"
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)
        self.assertEqual(response.data["detail"], "Fields cannot be empty")

    @patch("contact.views.send_contact_email")
    def test_post_success(self, mock_send_email):
        # Mock send_contact_email to return success
        mock_send_email.return_value = (True, None)
        data = {
            "fullname": "Test User",
            "email": "test@example.com",
            "subject": "Hello",
            "message": "Hi there"
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)
        self.assertEqual(
            response.data["detail"], "Message sent successfully, we will get back to you "
        )

    @patch("contact.views.send_contact_email")
    def test_post_failure(self, mock_send_email):
        # Mock send_contact_email to return failure
        mock_send_email.return_value = (False, "SMTP error")
        data = {
            "fullname": "Test User",
            "email": "test@example.com",
            "subject": "Hello",
            "message": "Hi there"
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)
        self.assertEqual(
            response.data["detail"], "Message could not be sent at this time. Please try again later"
        )

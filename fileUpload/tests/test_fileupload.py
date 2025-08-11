from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
import io

User = get_user_model()

class FileUploadAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create and authenticate user
        self.user = User.objects.create_user(
            first_name="john",
            last_name="Doe",
            email="test@example.com",
            password="testpassword123"
        )
        self.client.force_authenticate(user=self.user)

        self.file_upload_url = "/fileupload/upload/"
        self.tts_url = "/tts/generate/"

    def _create_test_file(self, filename="test.txt", content=b"Hello world"):
        return SimpleUploadedFile(filename, content, content_type="text/plain")

    # ---------- FILE UPLOAD TESTS ----------
    def test_file_upload_success(self):
        file = self._create_test_file()
        response = self.client.post(self.file_upload_url, {"file": file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text", response.data)  # assuming your view returns extracted text

    def test_file_upload_missing_file(self):
        response = self.client.post(self.file_upload_url, {}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_file_upload_invalid_file_type(self):
        file = SimpleUploadedFile("image.png", b"fakeimagebytes", content_type="image/png")
        response = self.client.post(self.file_upload_url, {"file": file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_file_upload_unauthenticated(self):
        self.client.force_authenticate(user=None)
        file = self._create_test_file()
        response = self.client.post(self.file_upload_url, {"file": file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

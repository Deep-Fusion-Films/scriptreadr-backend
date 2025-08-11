from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


class LoginAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/user/login'
        self.user_email = 'test@example'
        self.user_password = 'correct_password'
        self.user = User.objects.create_user(
            email=self.user_email,
            password=self.user_password
        )
        
    
        
      #test for empty fields in login form
    def test_empty_fields(self):
        payload = {
            'email': '',
            'password': self.user_password
            
        }
        
      
        response = self.client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('No empty field(s)', response.data['detail'])
    
    #test for incorrect password in login form
    def test_incorrect_password(self):
        
        payload = {
            'email': self.user_email,
            'password': 'incorrect_password'
            
        }
        
      
        response = self.client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('incorrect password', response.data['detail'])
        
    #test for unregistered user
    def test_unregistered_user_login(self):
        payload = {
            'email': 'ghostuser@email.com',
            'password': 'password'
            
        }
        
      
        response = self.client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('incorrect password', response.data['detail'])
        

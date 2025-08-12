from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
# Create your tests here.
 
User = get_user_model()
 
class RegisterAPITest(TestCase):
     def setUp(self):
        self.client = APIClient()
        self.url = '/user/register/'
        
        #test for successful registration
     def test_register_success(self):
        payload = {
            'first_name': 'john',
            'last_name': 'doe',
            'email': 'john@gmail.com',
            'password': '1234567',
            'confirm_password': '1234567' 
        }
        
        response = self.client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['email'], payload['email'])
        
        self.assertTrue(User.objects.filter(email=payload['email']).exists())
        
        #test for missing required fields
     def test_missing_first_name(self):
         payload = {
             'first_name': '',
             'last_name': 'Doe',
             'email': 'john@gmail.com',
             'password': '123456',
             'confirm_password': '123456'
         }
         
         response = self.client.post(self.url, data=payload, format='json')
         self.assertEqual(response.status_code, 400)
         self.assertIn('No empty field(s)', response.data['detail'])
    
    
        #test for password match
     def test_failed_password_match(self):
         payload = {
             'first_name': 'mike',
             'last_name': 'gee',
             'email': 'john@gmail.com',
             'password': '123456',
             'confirm_password': '12345'
         }
         
         response = self.client.post(self.url, data=payload, format='json')
         self.assertEqual(response.status_code, 400)
         self.assertIn('Passwords do not match', response.data['detail'])
    
    # #test if email is already in use
    #  def test_email_already_in_use(self):
    #      existing_user = User.objects.create_user(
    #          username='mike',
    #          first_name = 'mike',
    #          last_name = 'james',
    #          email= 'John@gmail.com',
    #          password= '12345'
    #      )
    #      payload = {
    #          'first_name': 'john',
    #          'last_name': 'Doe',
    #          'email': 'john@gmail.com',
    #          'password': '12345',
    #          'confirm_password': '12345'
    #      }
         
    #      response = self.client.post(self.url, data=payload, format='json')
    #      self.assertEqual(response.status_code, 400)
    #      self.assertIn('Email is already in use', response.data['detail'])

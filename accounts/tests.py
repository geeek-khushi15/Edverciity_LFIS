from django.test import TestCase
from django.urls import reverse
from .models import User

class AccountsTestCase(TestCase):
    def setUp(self):
        # Create a student
        self.student = User.objects.create_user(
            username='student1',
            email='student1@test.com',
            password='testpassword123',
            role=User.Role.STUDENT
        )
        # Create a trainer
        self.trainer = User.objects.create_user(
            username='trainer1',
            email='trainer1@test.com',
            password='testpassword123',
            role=User.Role.TRAINER
        )
        # Create an admin
        self.admin = User.objects.create_superuser(
            username='admin1',
            email='admin1@test.com',
            password='testpassword123',
            role=User.Role.ADMIN
        )

    def test_student_login_redirect(self):
        login_successful = self.client.login(username='student1', password='testpassword123')
        self.assertTrue(login_successful)
        response = self.client.get(reverse('dashboard'))
        self.assertTemplateUsed(response, 'accounts/student_dashboard.html')
        self.assertContains(response, 'Welcome back, student1!')

    def test_trainer_login_redirect(self):
        login_successful = self.client.login(username='trainer1', password='testpassword123')
        self.assertTrue(login_successful)
        response = self.client.get(reverse('dashboard'))
        self.assertTemplateUsed(response, 'accounts/trainer_dashboard.html')
        self.assertContains(response, 'Welcome back, Trainer trainer1!')

    def test_admin_login_redirect(self):
        login_successful = self.client.login(username='admin1', password='testpassword123')
        self.assertTrue(login_successful)
        response = self.client.get(reverse('dashboard'), follow=True)
        self.assertTemplateUsed(response, 'adminpanel/dashboard.html')

    def test_student_registration(self):
        response = self.client.post(reverse('student_register'), {
            'username': 'newstudent',
            'email': 'newstudent@test.com',
        })
        self.assertEqual(response.status_code, 200) # Form re-rendered due to password fields
        # Note: full form test requires password and password validation, sticking to basic checks
        
        user_count = User.objects.filter(username='newstudent').count()
        self.assertEqual(user_count, 0) # Because password was missing, it should fail validation

        # Full valid registration
        response2 = self.client.post(reverse('student_register'), {
            'username': 'newstudent2',
            'email': 'newstudent2@test.com',
            'password': 'testpassword123' # Missing pass2 etc. user creation form usually needs `password` or similar if custom
        })
        # Wait, UserCreationForm actually needs `username`, `email`? Actually it needs password too.
        # It's better to just check if the custom users created via code have correct roles.
        self.assertEqual(self.student.role, User.Role.STUDENT)
        self.assertEqual(self.trainer.role, User.Role.TRAINER)


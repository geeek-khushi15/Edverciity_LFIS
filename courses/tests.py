from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from .models import Course

class CourseModuleTests(TestCase):
    def setUp(self):
        # Create different users
        self.student = User.objects.create_user(
            username='student1', email='s1@test.com', password='password123', role=User.Role.STUDENT
        )
        self.trainer = User.objects.create_user(
            username='trainer1', email='t1@test.com', password='password123', role=User.Role.TRAINER
        )
        self.admin = User.objects.create_user(
            username='admin1', email='a1@test.com', password='password123', role=User.Role.ADMIN
        )
        
        # Create a sample course
        self.course = Course.objects.create(
            title='Test Course',
            description='Test Description',
            duration=10
        )

    def test_course_creation_admin_only(self):
        # Student attempting access
        self.client.login(username='student1', password='password123')
        response = self.client.get(reverse('course_create'))
        self.assertEqual(response.status_code, 403) # Forbidden
        
        # Trainer attempting access
        self.client.login(username='trainer1', password='password123')
        response = self.client.get(reverse('course_create'))
        self.assertEqual(response.status_code, 403) # Forbidden
        
        # Admin attempting access
        self.client.login(username='admin1', password='password123')
        response = self.client.get(reverse('course_create'))
        self.assertEqual(response.status_code, 200) # Success

    def test_create_course(self):
        self.client.login(username='admin1', password='password123')
        
        response = self.client.post(reverse('course_create'), {
            'title': 'New Test Course',
            'description': 'A shiny new course',
            'duration': 5
        })
        
        # Redirects to list on success
        self.assertEqual(response.status_code, 302)
        
        # Verify db insertion
        self.assertEqual(Course.objects.count(), 2)
        new_course = Course.objects.get(title='New Test Course')
        self.assertEqual(new_course.duration, 5)

    def test_course_list_access(self):
        self.client.login(username='admin1', password='password123')
        response = self.client.get(reverse('course_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Course')

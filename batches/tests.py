from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from courses.models import Course, CourseModule
from .models import Batch
import datetime

class BatchModuleTests(TestCase):
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
        self.module = CourseModule.objects.create(
            course=self.course,
            name='Core Module',
            description='Core topic set',
            order_number=1,
        )
        
        # Create a sample batch
        self.batch = Batch.objects.create(
            name='Test Batch 1',
            course=self.course,
            module=self.module,
            trainer=self.trainer,
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 6, 1)
        )

    def test_batch_creation_admin_only(self):
        # Student attempting access
        self.client.login(username='student1', password='password123')
        response = self.client.get(reverse('batch_create'))
        self.assertEqual(response.status_code, 403) # Forbidden
        
        # Trainer attempting access
        self.client.login(username='trainer1', password='password123')
        response = self.client.get(reverse('batch_create'))
        self.assertEqual(response.status_code, 403) # Forbidden
        
        # Admin attempting access
        self.client.login(username='admin1', password='password123')
        response = self.client.get(reverse('batch_create'))
        self.assertEqual(response.status_code, 200) # Success

    def test_create_batch(self):
        self.client.login(username='admin1', password='password123')
        
        response = self.client.post(reverse('batch_create'), {
            'name': 'New Test Batch',
            'course': self.course.id,
            'module': self.module.id,
            'trainer': self.trainer.id,
            'start_date': '2026-07-01',
            'end_date': '2026-12-01'
        })
        
        # Redirects to list on success
        self.assertEqual(response.status_code, 302)
        
        # Verify db insertion
        self.assertEqual(Batch.objects.count(), 2)
        new_batch = Batch.objects.get(name='New Test Batch')
        self.assertEqual(new_batch.course.id, self.course.id)

    def test_batch_list_access(self):
        self.client.login(username='admin1', password='password123')
        response = self.client.get(reverse('batch_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Batch 1')

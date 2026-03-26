from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import User
from courses.models import Course
from batches.models import Batch
from enrollments.models import Enrollment
from .models import Material
import datetime

class MaterialModuleTests(TestCase):
    def setUp(self):
        # Users
        self.student_enrolled = User.objects.create_user(
            username='student1', email='s1@test.com', password='password123', role=User.Role.STUDENT
        )
        self.student_not_enrolled = User.objects.create_user(
            username='student2', email='s2@test.com', password='password123', role=User.Role.STUDENT
        )
        self.trainer_owner = User.objects.create_user(
            username='trainer1', email='t1@test.com', password='password123', role=User.Role.TRAINER
        )
        self.trainer_other = User.objects.create_user(
            username='trainer2', email='t2@test.com', password='password123', role=User.Role.TRAINER
        )
        self.admin = User.objects.create_user(
            username='admin1', email='a1@test.com', password='password123', role=User.Role.ADMIN
        )
        
        # Course & Batch Setup
        self.course = Course.objects.create(title='React Native Masterclass', duration=50)
        self.batch = Batch.objects.create(
            name='Summer React Cohort', course=self.course, trainer=self.trainer_owner,
            start_date=datetime.date(2026, 6, 1), end_date=datetime.date(2026, 8, 1)
        )
        
        # Enroll active student
        self.enrollment = Enrollment.objects.create(student=self.student_enrolled, batch=self.batch)
        
        # Existing Material
        self.material = Material.objects.create(
            title='Intro Notes', batch=self.batch, material_type='NOTE', content='Welcome to React!'
        )

    def test_upload_material_access_trainer_only(self):
        # Admin
        self.client.login(username='admin1', password='password123')
        self.assertEqual(self.client.get(reverse('material_create')).status_code, 403)
        
        # Student
        self.client.login(username='student1', password='password123')
        self.assertEqual(self.client.get(reverse('material_create')).status_code, 403)
        
        # Trainer
        self.client.login(username='trainer1', password='password123')
        self.assertEqual(self.client.get(reverse('material_create')).status_code, 200)

    def test_upload_material(self):
        self.client.login(username='trainer1', password='password123')
        
        # Test creating a LINK material
        response = self.client.post(reverse('material_create'), {
            'title': 'Redux Documentation',
            'batch': self.batch.id,
            'material_type': 'LINK',
            'content': 'https://redux.js.org'
        })
        
        self.assertEqual(response.status_code, 302) # Redirects to trainer dashboard or next
        self.assertEqual(Material.objects.count(), 2)
        
    def test_list_materials_access_rules(self):
        url = reverse('material_list', kwargs={'batch_id': self.batch.id})
        
        # Admin can't see it via this view
        self.client.login(username='admin1', password='password123')
        queryset = self.client.get(url).context['materials']
        self.assertEqual(len(queryset), 0)
        
        # Unenrolled student shouldn't see materials
        self.client.login(username='student2', password='password123')
        queryset = self.client.get(url).context['materials']
        self.assertEqual(len(queryset), 0)
        
        # Other trainer shouldn't see materials
        self.client.login(username='trainer2', password='password123')
        queryset = self.client.get(url).context['materials']
        self.assertEqual(len(queryset), 0)
        
        # Enrolled student should see materials
        self.client.login(username='student1', password='password123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['materials']), 1)
        self.assertContains(response, 'Intro Notes')
        
        # Trainer owner should see materials
        self.client.login(username='trainer1', password='password123')
        response = self.client.get(url)
        self.assertEqual(len(response.context['materials']), 1)

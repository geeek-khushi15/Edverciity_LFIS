from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from courses.models import Course
from batches.models import Batch
from enrollments.models import Enrollment
from recommendations.models import Recommendation
from certifications.models import CertificationApplication, Certificate
import datetime

class CertificationModuleTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(username='student1', email='s@test.com', password='password123', role=User.Role.STUDENT)
        self.other_student = User.objects.create_user(username='student2', email='s2@test.com', password='password123', role=User.Role.STUDENT)
        self.trainer = User.objects.create_user(username='trainer1', email='t1@test.com', password='password123', role=User.Role.TRAINER)
        self.admin = User.objects.create_user(username='admin1', email='a1@test.com', password='password123', role=User.Role.ADMIN)
        
        self.course = Course.objects.create(title='AI Mastery', duration=30)
        self.batch = Batch.objects.create(name='AI Cohort', course=self.course, trainer=self.trainer, start_date=datetime.date(2026, 1, 1), end_date=datetime.date(2026, 2, 1))
        self.enrollment = Enrollment.objects.create(student=self.student, batch=self.batch)

    def test_certification_list_access(self):
        self.client.login(username='admin1', password='password123')
        self.assertEqual(self.client.get(reverse('student_certification_list')).status_code, 403)
        self.client.login(username='trainer1', password='password123')
        self.assertEqual(self.client.get(reverse('student_certification_list')).status_code, 403)
        self.client.login(username='student1', password='password123')
        self.assertEqual(self.client.get(reverse('student_certification_list')).status_code, 200)

    def test_certification_list_visibility(self):
        self.client.login(username='student1', password='password123')
        response = self.client.get(reverse('student_certification_list'))
        self.assertContains(response, 'AI Cohort')
        self.client.logout()

    def test_apply_without_recommendation(self):
        self.client.login(username='student1', password='password123')
        response = self.client.post(reverse('apply_certification', kwargs={'batch_id': self.batch.id}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CertificationApplication.objects.count(), 0)

    def test_apply_with_recommendation(self):
        self.client.login(username='student1', password='password123')
        Recommendation.objects.create(student=self.student, batch=self.batch, recommended_by=self.trainer)
        form_data = {
            'full_name': 'Student One',
            'fathers_name': 'Father One',
            'mothers_name': 'Mother One',
            'date_of_birth': '2000-01-01',
            'email_id': 's@test.com',
            'contact_number': '9876543210',
            'course_start_date': '2026-01-01',
            'course_end_date': '2026-02-01',
            'caste_category': 'GENERAL',
            'highest_education': 'UG',
            'address_with_pincode': '123 Test Street, 400001',
        }
        response = self.client.post(reverse('apply_certification', kwargs={'batch_id': self.batch.id}), form_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CertificationApplication.objects.count(), 1)

    def test_prevent_duplicate_application(self):
        self.client.login(username='student1', password='password123')
        Recommendation.objects.create(student=self.student, batch=self.batch, recommended_by=self.trainer)
        form_data = {
            'full_name': 'Student One',
            'fathers_name': 'Father One',
            'mothers_name': 'Mother One',
            'date_of_birth': '2000-01-01',
            'email_id': 's@test.com',
            'contact_number': '9876543210',
            'course_start_date': '2026-01-01',
            'course_end_date': '2026-02-01',
            'caste_category': 'GENERAL',
            'highest_education': 'UG',
            'address_with_pincode': '123 Test Street, 400001',
        }
        self.client.post(reverse('apply_certification', kwargs={'batch_id': self.batch.id}), form_data)
        response = self.client.post(reverse('apply_certification', kwargs={'batch_id': self.batch.id}), form_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CertificationApplication.objects.count(), 1)

class AdminCertificationTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(username='student1', email='s@test.com', password='password123', role=User.Role.STUDENT)
        self.trainer = User.objects.create_user(username='trainer1', email='t1@test.com', password='password123', role=User.Role.TRAINER)
        self.admin = User.objects.create_user(username='admin1', email='a1@test.com', password='password123', role=User.Role.ADMIN)
        
        self.course = Course.objects.create(title='AI Mastery', duration=30)
        self.batch = Batch.objects.create(name='AI Cohort', course=self.course, trainer=self.trainer, start_date=datetime.date(2026, 1, 1), end_date=datetime.date(2026, 2, 1))
        self.enrollment = Enrollment.objects.create(student=self.student, batch=self.batch)
        self.recommendation = Recommendation.objects.create(student=self.student, batch=self.batch, recommended_by=self.trainer)
        self.application = CertificationApplication.objects.create(student=self.student, batch=self.batch)

    def test_admin_list_access(self):
        self.client.login(username='student1', password='password123')
        self.assertEqual(self.client.get(reverse('admin_application_list')).status_code, 403)
        self.client.login(username='admin1', password='password123')
        self.assertEqual(self.client.get(reverse('admin_application_list')).status_code, 200)

    def test_admin_approve_application(self):
        self.client.login(username='admin1', password='password123')
        response = self.client.post(reverse('approve_application', kwargs={'app_id': self.application.id}))
        self.assertEqual(response.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'APPROVED')
        self.assertEqual(Certificate.objects.count(), 1)

    def test_admin_reject_application(self):
        self.client.login(username='admin1', password='password123')
        response = self.client.post(reverse('reject_application', kwargs={'app_id': self.application.id}))
        self.assertEqual(response.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'REJECTED')
        self.assertEqual(Certificate.objects.count(), 0)

    def test_cant_double_evaluate(self):
        self.client.login(username='admin1', password='password123')
        self.client.post(reverse('approve_application', kwargs={'app_id': self.application.id}))
        response = self.client.post(reverse('reject_application', kwargs={'app_id': self.application.id}))
        self.assertEqual(response.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'APPROVED')

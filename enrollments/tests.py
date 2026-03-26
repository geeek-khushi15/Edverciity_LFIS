from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from courses.models import Course
from batches.models import Batch
from .models import Enrollment
import datetime

class EnrollmentModuleTests(TestCase):
    def setUp(self):
        # Create users
        self.student1 = User.objects.create_user(
            username='student1', email='s1@test.com', password='password123', role=User.Role.STUDENT
        )
        self.student2 = User.objects.create_user(
            username='student2', email='s2@test.com', password='password123', role=User.Role.STUDENT
        )
        self.admin = User.objects.create_user(
            username='admin1', email='a1@test.com', password='password123', role=User.Role.ADMIN
        )
        
        # Create course & batch
        self.course = Course.objects.create(title='Python 101', duration=40)
        self.batch = Batch.objects.create(
            name='Python Morning',
            course=self.course,
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 3, 1)
        )
        
        # Enroll student1
        self.enrollment = Enrollment.objects.create(
            student=self.student1,
            batch=self.batch
        )

    def test_enrollment_access_student_only(self):
        # Enrollment create is now admin-only (refactored to admin-enrollment model)
        self.client.login(username='admin1', password='password123')
        response = self.client.get(reverse('enrollment_create'))
        self.assertEqual(response.status_code, 200)  # Admin can access

        # Non-admin users are forbidden
        self.client.login(username='student2', password='password123')
        response = self.client.get(reverse('enrollment_create'))
        self.assertEqual(response.status_code, 403)

    def test_create_enrollment(self):
        # Only admin can create enrollments now
        self.client.login(username='admin1', password='password123')

        response = self.client.post(reverse('enrollment_create'), {
            'student': self.student2.id,
            'course': self.course.id,
            'batch': self.batch.id,
            'enrollment_type': 'FULL',
        })

        # Redirect on success
        self.assertEqual(response.status_code, 302)

        self.assertEqual(Enrollment.objects.count(), 2)
        self.assertTrue(Enrollment.objects.filter(student=self.student2, batch=self.batch).exists())

    def test_duplicate_enrollment_prevention(self):
        # Admin tries to enroll student1 who is already enrolled
        self.client.login(username='admin1', password='password123')

        response = self.client.post(reverse('enrollment_create'), {
            'student': self.student1.id,
            'course': self.course.id,
            'batch': self.batch.id,
            'enrollment_type': 'FULL',
        })

        # Should rerender form (status 200) rather than standard success redirect (302)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Enrollment.objects.count(), 1)  # No new enrollment created

    def test_enrollment_list_privacy(self):
        self.client.login(username='student2', password='password123')
        response = self.client.get(reverse('enrollment_list'))
        
        self.assertEqual(response.status_code, 200)
        # student2 shouldn't see Python Morning since only student1 is enrolled
        self.assertNotContains(response, 'Python Morning')
        
        self.client.logout()
        
        self.client.login(username='student1', password='password123')
        response = self.client.get(reverse('enrollment_list'))
        self.assertContains(response, 'Python Morning')

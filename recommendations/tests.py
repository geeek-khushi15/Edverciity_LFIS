from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from courses.models import Course
from batches.models import Batch
from enrollments.models import Enrollment
from .models import Recommendation
import datetime

class RecommendationModuleTests(TestCase):
    def setUp(self):
        # Users
        self.student = User.objects.create_user(
            username='student1', email='s@test.com', password='password123', role=User.Role.STUDENT
        )
        self.other_student = User.objects.create_user(
            username='student2', email='s2@test.com', password='password123', role=User.Role.STUDENT
        )
        self.trainer = User.objects.create_user(
            username='trainer1', email='t1@test.com', password='password123', role=User.Role.TRAINER
        )
        self.other_trainer = User.objects.create_user(
            username='trainer2', email='t2@test.com', password='password123', role=User.Role.TRAINER
        )
        self.admin = User.objects.create_user(
            username='admin1', email='a1@test.com', password='password123', role=User.Role.ADMIN
        )
        
        # Course & Batch Setup
        self.course = Course.objects.create(title='Python Core', duration=30)
        self.batch = Batch.objects.create(
            name='Python Morning', course=self.course, trainer=self.trainer,
            start_date=datetime.date(2026, 1, 1), end_date=datetime.date(2026, 2, 1)
        )
        
        # Enroll active student
        self.enrollment = Enrollment.objects.create(student=self.student, batch=self.batch)

    def test_performance_list_access(self):
        # Admin
        self.client.login(username='admin1', password='password123')
        self.assertEqual(self.client.get(reverse('student_performance_list')).status_code, 403)
        # Student
        self.client.login(username='student1', password='password123')
        self.assertEqual(self.client.get(reverse('student_performance_list')).status_code, 403)
        # Trainer
        self.client.login(username='trainer1', password='password123')
        self.assertEqual(self.client.get(reverse('student_performance_list')).status_code, 200)

    def test_performance_list_visibility(self):
        self.client.login(username='trainer1', password='password123')
        response = self.client.get(reverse('student_performance_list'))
        # Trainer 1 should see student1 in Python Morning batch
        self.assertContains(response, 'student1')
        self.assertContains(response, 'Python Morning')

        self.client.logout()
        
        # Other trainer should not see the student since they don't own the batch
        self.client.login(username='trainer2', password='password123')
        response = self.client.get(reverse('student_performance_list'))
        self.assertNotContains(response, 'student1')
        self.assertNotContains(response, 'Python Morning')

    def test_recommend_student_success(self):
        self.client.login(username='trainer1', password='password123')
        response = self.client.post(reverse('recommend_student', kwargs={'student_id': self.student.id, 'batch_id': self.batch.id}))
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Recommendation.objects.count(), 1)
        rec = Recommendation.objects.first()
        self.assertEqual(rec.student, self.student)
        self.assertEqual(rec.batch, self.batch)
        self.assertEqual(rec.status, 'PENDING')
        self.assertEqual(rec.recommended_by, self.trainer)

    def test_prevent_duplicate_recommendation(self):
        # Create a recommendation manually first
        Recommendation.objects.create(student=self.student, batch=self.batch, recommended_by=self.trainer)
        self.assertEqual(Recommendation.objects.count(), 1)
        
        self.client.login(username='trainer1', password='password123')
        response = self.client.post(reverse('recommend_student', kwargs={'student_id': self.student.id, 'batch_id': self.batch.id}))
        
        # Should redirect but count remains 1
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Recommendation.objects.count(), 1)

    def test_unauthorized_recommendation(self):
        self.client.login(username='trainer2', password='password123')
        
        # trainer2 tries to recommend student1 for trainer1's batch
        response = self.client.post(reverse('recommend_student', kwargs={'student_id': self.student.id, 'batch_id': self.batch.id}))
        
        # Fails validation
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Recommendation.objects.count(), 0)

    def test_unenrolled_student_recommendation(self):
        self.client.login(username='trainer1', password='password123')
        
        # trainer1 tries to recommend other_student (who is not enrolled in the batch)
        response = self.client.post(reverse('recommend_student', kwargs={'student_id': self.other_student.id, 'batch_id': self.batch.id}))
        
        # Fails formal enrollment validation
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Recommendation.objects.count(), 0)

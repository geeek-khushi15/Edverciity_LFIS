from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from courses.models import Course
from batches.models import Batch
from enrollments.models import Enrollment
from .models import Test as AssessmentTest, Question, TestAttempt
import datetime

class TestModuleTests(TestCase):
    def setUp(self):
        # Users
        self.student_enrolled = User.objects.create_user(
            username='student1', email='s1@test.com', password='password123', role=User.Role.STUDENT
        )
        self.student_not_enrolled = User.objects.create_user(
            username='student2', email='s2@test.com', password='password123', role=User.Role.STUDENT
        )
        self.trainer = User.objects.create_user(
            username='trainer1', email='t1@test.com', password='password123', role=User.Role.TRAINER
        )
        self.admin = User.objects.create_user(
            username='admin1', email='a1@test.com', password='password123', role=User.Role.ADMIN
        )
        
        # Course & Batch Setup
        self.course = Course.objects.create(title='Django Testing', duration=10)
        self.batch = Batch.objects.create(
            name='Test Batch', course=self.course, trainer=self.trainer,
            start_date=datetime.date(2026, 1, 1), end_date=datetime.date(2026, 2, 1)
        )
        
        self.enrollment = Enrollment.objects.create(student=self.student_enrolled, batch=self.batch)
        
        # Create Test
        self.test_obj = AssessmentTest.objects.create(
            title='Midterm Exam', batch=self.batch, passing_marks=1
        )
        self.question = Question.objects.create(
            test=self.test_obj,
            text='What is Django?',
            option1='A web framework', option2='A car', option3='A drink', option4='A movie',
            correct_option=1
        )

    def test_create_test_access(self):
        # Admin
        self.client.login(username='admin1', password='password123')
        self.assertEqual(self.client.get(reverse('test_create')).status_code, 403)
        # Trainer
        self.client.login(username='trainer1', password='password123')
        self.assertEqual(self.client.get(reverse('test_create')).status_code, 200)

    def test_student_test_list_visibility(self):
        # Enrolled student sees the test
        self.client.login(username='student1', password='password123')
        response = self.client.get(reverse('student_test_list'))
        self.assertContains(response, 'Midterm Exam')
        
        self.client.logout()
        # Unenrolled student does not see the test
        self.client.login(username='student2', password='password123')
        response = self.client.get(reverse('student_test_list'))
        self.assertNotContains(response, 'Midterm Exam')

    def test_student_attempt_evaluation(self):
        self.client.login(username='student1', password='password123')
        
        # Submit correct answer (Option 1)
        response = self.client.post(reverse('test_attempt', kwargs={'test_id': self.test_obj.id}), {
            f'question_{self.question.id}': '1'
        })
        
        self.assertEqual(response.status_code, 302) # Redirects to dashboard
        
        # Verify TestAttempt score
        attempt = TestAttempt.objects.get(student=self.student_enrolled, test=self.test_obj)
        self.assertEqual(attempt.score, 1)
        self.assertTrue(attempt.is_passed)

    def test_prevent_duplicate_attempt(self):
        self.client.login(username='student1', password='password123')
        
        # First attempt
        self.client.post(reverse('test_attempt', kwargs={'test_id': self.test_obj.id}), {
            f'question_{self.question.id}': '2' # Wrong answer
        })
        
        self.assertEqual(TestAttempt.objects.count(), 1)
        
        # Second attempt
        response = self.client.post(reverse('test_attempt', kwargs={'test_id': self.test_obj.id}), {
            f'question_{self.question.id}': '1' # Correct answer this time
        })
        
        # Count should remain 1, new attempt rejected
        self.assertEqual(TestAttempt.objects.count(), 1)
        
        # The score should still be 0 logically
        attempt = TestAttempt.objects.get(student=self.student_enrolled, test=self.test_obj)
        self.assertEqual(attempt.score, 0)

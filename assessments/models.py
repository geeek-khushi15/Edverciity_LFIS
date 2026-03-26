from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User
from batches.models import Batch
from courses.models import Course, CourseModule


class Assignment(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    module = models.ForeignKey(CourseModule, on_delete=models.SET_NULL, null=True, blank=True, related_name='assignments')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='assignments')
    trainer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_assignments',
        limit_choices_to={'role': 'TRAINER'}
    )
    due_date = models.DateTimeField()
    max_marks = models.PositiveIntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.batch.name}"


class AssignmentSubmission(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        REVIEWED = 'REVIEWED', 'Reviewed'

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assignment_submissions',
        limit_choices_to={'role': 'STUDENT'}
    )
    file_upload = models.FileField(upload_to='assignment_submissions/')
    submitted_at = models.DateTimeField(auto_now_add=True)
    marks_obtained = models.PositiveIntegerField(blank=True, null=True)
    feedback = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    class Meta:
        unique_together = ('assignment', 'student')
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.assignment.title} - {self.student.username}"

class Test(models.Model):
    title = models.CharField(max_length=200)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='tests', blank=True, null=True)
    module = models.ForeignKey(CourseModule, on_delete=models.SET_NULL, null=True, blank=True, related_name='tests')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='tests')
    trainer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_tests',
        limit_choices_to={'role': 'TRAINER'},
        blank=True,
        null=True
    )
    total_marks = models.PositiveIntegerField(default=100)
    duration = models.PositiveIntegerField(default=30, help_text='Duration in minutes')
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    passing_marks = models.PositiveIntegerField(default=40, help_text="Minimum marks to pass")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.batch.name}"
        
    @property
    def question_count(self):
        return self.questions.count()

class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField(help_text="The question text.")
    question_text = models.TextField(blank=True, default='')
    option1 = models.CharField(max_length=255)
    option_a = models.CharField(max_length=255, blank=True, default='')
    option2 = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255, blank=True, default='')
    option3 = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255, blank=True, default='')
    option4 = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255, blank=True, default='')
    
    correct_option = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        help_text="Select 1, 2, 3, or 4."
    )
    correct_answer = models.CharField(
        max_length=1,
        choices=(('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')),
        blank=True,
        default=''
    )

    def __str__(self):
        return f"Q: {self.text[:50]}"

class TestAttempt(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'STUDENT'}, related_name='test_attempts')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='attempts')
    score = models.IntegerField(default=0)
    attempted_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        # A student should only be able to attempt a specific test once.
        unique_together = ('student', 'test')

    def __str__(self):
        return f"{self.student.username} - {self.test.title} ({self.score})"
        
    @property
    def is_passed(self):
        return self.score >= self.test.passing_marks

from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):

    class Role(models.TextChoices):
        SUPERADMIN = 'SUPERADMIN', 'Super Admin'
        ADMIN = 'ADMIN', 'Admin'
        TRAINER = 'TRAINER', 'Trainer'
        STUDENT = 'STUDENT', 'Student'

    role = models.CharField(max_length=15, choices=Role.choices, default=Role.STUDENT)
    email = models.EmailField(unique=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class TrainerProfile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'TRAINER'},
        related_name='trainer_profile'
    )

    face_descriptor = models.TextField(
        help_text="JSON serialized array of 128 Face API encodings",
        null=True,
        blank=True
    )

    is_setup_complete = models.BooleanField(default=False)

    profile_photo = models.ImageField(upload_to='trainer_photos/', blank=True, null=True)
    full_name = models.CharField(max_length=200, blank=True, null=True)
    father_name = models.CharField(max_length=200, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True, null=True)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)

    trainer_id = models.CharField(max_length=30, blank=True, null=True)
    department = models.CharField(max_length=120, blank=True, null=True)
    highest_education = models.CharField(max_length=200, blank=True, null=True)
    years_of_experience = models.PositiveIntegerField(blank=True, null=True)
    specialization = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - Setup: {self.is_setup_complete}"


class EmployeeAttendanceLog(models.Model):

    trainer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'TRAINER'},
        related_name='attendance_logs'
    )

    date = models.DateField(auto_now_add=True)

    login_time = models.TimeField(null=True, blank=True)
    logout_time = models.TimeField(null=True, blank=True)

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    face_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ['-date', '-login_time']

    def __str__(self):
        return f"{self.trainer.username} - {self.date}"


# ===============================
# Student Detailed Profile Model
# ===============================

class StudentProfile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    full_name = models.CharField(max_length=200, blank=True, null=True)
    father_name = models.CharField(max_length=200, blank=True, null=True)
    mother_name = models.CharField(max_length=200, blank=True, null=True)

    date_of_birth = models.DateField(blank=True, null=True)

    contact_number = models.CharField(max_length=15, blank=True, null=True)

    caste_category = models.CharField(max_length=100, blank=True, null=True)

    highest_education = models.CharField(max_length=200, blank=True, null=True)

    address = models.TextField(blank=True, null=True)

    pincode = models.CharField(max_length=10, blank=True, null=True)

    course_start_date = models.DateField(blank=True, null=True)

    course_end_date = models.DateField(blank=True, null=True)

    profile_photo = models.ImageField(upload_to='student_photos/', blank=True, null=True)


class StudentDoubt(models.Model):

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        RESOLVED = 'RESOLVED', 'Resolved'

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='raised_doubts',
        limit_choices_to={'role': 'STUDENT'}
    )

    trainer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='assigned_doubts',
        limit_choices_to={'role': 'TRAINER'},
        null=True,
        blank=True
    )

    title = models.CharField(max_length=200, default='')
    description = models.TextField()
    response = models.TextField(blank=True)

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )

    related_course = models.ForeignKey(
        'courses.Course',
        on_delete=models.SET_NULL,
        related_name='doubts',
        null=True,
        blank=True
    )

    related_session = models.ForeignKey(
        'attendance.ClassSession',
        on_delete=models.SET_NULL,
        related_name='doubts',
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.username} - {self.title}"
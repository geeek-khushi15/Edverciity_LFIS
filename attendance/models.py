from django.db import models
from django.core.exceptions import ValidationError
from accounts.models import User
from batches.models import Batch
from courses.models import Course, CourseModule, CourseTopic

class ClassSession(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='sessions')
    date = models.DateField()
    # topics_covered is kept for backwards compatibility or as a summary, but granular tracking is done via SessionTopic
    topics_covered = models.TextField(help_text="Describe the topics covered in this session", blank=True)
    trainer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, limit_choices_to={'role': 'TRAINER'}, related_name='conducted_sessions')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.batch.name} - {self.date}"

class SessionTopic(models.Model):
    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name='topics')
    topic_name = models.CharField(max_length=255)
    trainer_taught = models.BooleanField(default=False)
    taught_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.topic_name} - {self.session.date}"

class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = 'PRESENT', 'Present'
        ABSENT = 'ABSENT', 'Absent'

    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name='attendances')
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'STUDENT'}, related_name='session_attendances')
    is_present = models.BooleanField(default=True)
    trainer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'TRAINER'},
        related_name='marked_attendance_records'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendance_records'
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendance_records'
    )
    session_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PRESENT
    )
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('session', 'student')

    def __str__(self):
        status = self.get_status_display() if self.status else ("Present" if self.is_present else "Absent")
        session_label = self.session_date or self.session.date
        return f"{self.student.username} - {session_label} ({status})"

class TopicAcknowledgement(models.Model):
    session_topic = models.ForeignKey(SessionTopic, on_delete=models.CASCADE, related_name='acknowledgements')
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'STUDENT'}, related_name='topic_acknowledgements')
    student_understood = models.BooleanField(default=False)
    understood_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('session_topic', 'student')

    def __str__(self):
        status = "Understood" if self.student_understood else "Pending"
        return f"{self.student.username} - {self.session_topic.topic_name} ({status})"


class AttendanceSession(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='attendance_sessions')
    module = models.ForeignKey(CourseModule, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_sessions')
    topic = models.ForeignKey(CourseTopic, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_sessions')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='attendance_sessions')
    trainer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'TRAINER'},
        related_name='attendance_sessions'
    )
    session_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-session_date', '-created_at']
        constraints = [
            models.UniqueConstraint(fields=['batch', 'topic', 'session_date'], name='unique_attendance_session_per_batch_topic_date')
        ]

    def clean(self):
        super().clean()
        if self.batch_id and self.course_id and self.batch.course_id != self.course_id:
            raise ValidationError('Selected batch must belong to the selected course.')
        if self.topic_id:
            if self.topic.course_id != self.course_id:
                raise ValidationError('Selected topic must belong to the selected course.')
            if self.module_id and self.topic.module_id != self.module_id:
                raise ValidationError('Selected topic must belong to the selected module.')
            if not self.module_id:
                self.module_id = self.topic.module_id
        if self.batch_id and self.batch.module_id and self.module_id and self.batch.module_id != self.module_id:
            raise ValidationError('Selected module must match the batch module.')

    def save(self, *args, **kwargs):
        if self.topic_id and not self.module_id:
            self.module_id = self.topic.module_id
        if self.batch_id and not self.course_id:
            self.course_id = self.batch.course_id
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.batch.name} - {self.session_date}"


class AttendanceRecord(models.Model):
    class Status(models.TextChoices):
        PRESENT = 'PRESENT', 'Present'
        ABSENT = 'ABSENT', 'Absent'

    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='records')
    module = models.ForeignKey(CourseModule, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_records')
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'STUDENT'},
        related_name='attendance_records'
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PRESENT)
    marked_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('session', 'student')
        ordering = ['student__username']

    def __str__(self):
        return f"{self.student.username} - {self.session.session_date} ({self.get_status_display()})"

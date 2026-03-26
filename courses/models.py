from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

from accounts.models import User

class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    duration = models.PositiveIntegerField(help_text="Duration in hours")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title


class CourseModule(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order_number = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['course__title', 'order_number', 'id']
        unique_together = ('course', 'name')

    def __str__(self):
        return f"{self.course.title} - {self.name}"


class CourseTopic(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='topics')
    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE, related_name='topics', null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    topic_number = models.IntegerField()
    resources_link = models.URLField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_course_topics')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['course__title', 'module__order_number', 'topic_number', 'id']
        constraints = [
            models.UniqueConstraint(fields=['module', 'topic_number'], name='unique_topic_number_per_module')
        ]

    def clean(self):
        super().clean()
        if self.module_id and self.module.course_id != self.course_id:
            raise ValidationError('Selected module must belong to the selected course.')

    def save(self, *args, **kwargs):
        if self.module_id and not self.course_id:
            self.course_id = self.module.course_id
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.course.title} - Topic {self.topic_number}: {self.title}"


class TopicAcknowledgement(models.Model):
    topic = models.ForeignKey(CourseTopic, on_delete=models.CASCADE, related_name='acknowledgements')
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': User.Role.STUDENT},
        related_name='course_topic_acknowledgements'
    )
    acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ('topic', 'student')

    def mark_acknowledged(self):
        self.acknowledged = True
        self.acknowledged_at = self.acknowledged_at or timezone.now()

    def __str__(self):
        status = 'Acknowledged' if self.acknowledged else 'Pending'
        return f"{self.student.username} - {self.topic.title} ({status})"


class TopicProgress(models.Model):
    topic = models.ForeignKey(CourseTopic, on_delete=models.CASCADE, related_name='progress_records')
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': User.Role.STUDENT},
        related_name='topic_progress_student_records',
    )
    trainer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': User.Role.TRAINER},
        related_name='topic_progress_trainer_records',
    )

    trainer_marked_taught = models.BooleanField(default=False)
    trainer_marked_at = models.DateTimeField(null=True, blank=True)

    student_marked_understood = models.BooleanField(default=False)
    student_marked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('topic', 'student', 'trainer')
        ordering = ['topic__course__title', 'topic__topic_number', 'student__username']

    def clean(self):
        if not self.pk:
            return

        original = TopicProgress.objects.get(pk=self.pk)

        if original.topic_id != self.topic_id or original.student_id != self.student_id or original.trainer_id != self.trainer_id:
            raise ValidationError('TopicProgress identity fields cannot be changed once created.')

        if original.trainer_marked_taught and not self.trainer_marked_taught:
            raise ValidationError('Trainer taught acknowledgement cannot be changed once marked.')

        if original.trainer_marked_taught and self.trainer_marked_at != original.trainer_marked_at:
            raise ValidationError('Trainer taught timestamp cannot be changed once marked.')

        if original.student_marked_understood and not self.student_marked_understood:
            raise ValidationError('Student understood acknowledgement cannot be changed once marked.')

        if original.student_marked_understood and self.student_marked_at != original.student_marked_at:
            raise ValidationError('Student understood timestamp cannot be changed once marked.')

    def save(self, *args, **kwargs):
        if self.trainer_marked_taught and self.trainer_marked_at is None:
            self.trainer_marked_at = timezone.now()

        if self.student_marked_understood and self.student_marked_at is None:
            self.student_marked_at = timezone.now()

        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        taught = 'Taught' if self.trainer_marked_taught else 'Not taught'
        understood = 'Understood' if self.student_marked_understood else 'Not understood'
        return f"{self.topic.title} | {self.student.username} | {taught}, {understood}"

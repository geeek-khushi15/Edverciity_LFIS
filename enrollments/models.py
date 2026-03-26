from django.db import models
from django.db.models import Q
from accounts.models import User
from batches.models import Batch
from courses.models import Course, CourseModule

class Enrollment(models.Model):
    class EnrollmentType(models.TextChoices):
        FULL = 'FULL', 'Full Course'
        MODULE = 'MODULE', 'Module'

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'STUDENT'},
        related_name='enrollments'
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments', null=True, blank=True)
    module = models.ForeignKey(CourseModule, on_delete=models.SET_NULL, null=True, blank=True, related_name='enrollments')
    enrollment_type = models.CharField(max_length=10, choices=EnrollmentType.choices, default=EnrollmentType.FULL)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='enrollments')
    enrollment_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['student', 'batch', 'module'], name='unique_student_batch_module_enrollment'),
            models.CheckConstraint(
                condition=(
                    Q(enrollment_type='FULL', module__isnull=True) |
                    Q(enrollment_type='MODULE', module__isnull=False)
                ),
                name='enrollment_type_module_consistency'
            ),
        ]

    @property
    def enrolled_at(self):
        # Alias for updated naming while keeping DB compatibility.
        return self.enrollment_date

    def clean(self):
        super().clean()
        if self.batch_id and self.course_id and self.batch.course_id != self.course_id:
            from django.core.exceptions import ValidationError
            raise ValidationError('Selected batch must belong to the selected course.')

        if self.module_id:
            if self.module.course_id != self.course_id:
                from django.core.exceptions import ValidationError
                raise ValidationError('Selected module must belong to the selected course.')

        if self.batch_id and self.batch.module_id and self.enrollment_type == self.EnrollmentType.MODULE:
            if not self.module_id:
                from django.core.exceptions import ValidationError
                raise ValidationError('Module enrollment requires a module selection.')
            if self.batch.module_id != self.module_id:
                from django.core.exceptions import ValidationError
                raise ValidationError('Selected batch does not match the selected module.')

    def save(self, *args, **kwargs):
        if self.batch_id and not self.course_id:
            self.course_id = self.batch.course_id
        super().save(*args, **kwargs)

    @classmethod
    def has_module_access(cls, student, batch, module=None):
        base_qs = cls.objects.filter(student=student, batch=batch)
        if module is None:
            return base_qs.exists()
        return base_qs.filter(
            Q(enrollment_type=cls.EnrollmentType.FULL) |
            Q(enrollment_type=cls.EnrollmentType.MODULE, module=module)
        ).exists()

    def __str__(self):
        if self.enrollment_type == self.EnrollmentType.MODULE and self.module:
            label = self.module.name
        else:
            label = self.course.title if self.course else self.batch.course.title
        return f"{self.student.get_full_name() or self.student.username} - {label} ({self.batch.name})"

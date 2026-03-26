from django.db import models
from django.core.exceptions import ValidationError
from courses.models import Course, CourseModule
from accounts.models import User

class Batch(models.Model):
    name = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='batches')
    module = models.ForeignKey(CourseModule, on_delete=models.SET_NULL, null=True, blank=True, related_name='batches')
    trainer = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        limit_choices_to={'role': 'TRAINER'},
        related_name='trainer_batches'
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    def clean(self):
        super().clean()
        if self.module_id and self.module.course_id != self.course_id:
            raise ValidationError('Selected module must belong to the selected course.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.course.title}"

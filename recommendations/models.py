from django.db import models
from accounts.models import User
from batches.models import Batch

class Recommendation(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = 'PENDING', 'Pending Admin Approval'
        APPROVED = 'APPROVED', 'Approved by Admin'
        REJECTED = 'REJECTED', 'Rejected'

    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'STUDENT'}, related_name='recommendations')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='recommendations')
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    recommended_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, limit_choices_to={'role': 'TRAINER'}, related_name='recommendations_made')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'batch')

    def __str__(self):
        return f"{self.student.username} recommended by {self.recommended_by.username if self.recommended_by else 'Unknown'} for {self.batch.name} ({self.get_status_display()})"

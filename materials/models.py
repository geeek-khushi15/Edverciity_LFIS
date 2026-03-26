from django.db import models
from batches.models import Batch
import os

class Material(models.Model):
    class MaterialType(models.TextChoices):
        PDF = 'PDF', 'PDF Document'
        VIDEO = 'VIDEO', 'Video File'
        NOTE = 'NOTE', 'Text Note'
        LINK = 'LINK', 'External Link'

    title = models.CharField(max_length=200)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='materials')
    material_type = models.CharField(max_length=10, choices=MaterialType.choices, default=MaterialType.PDF)
    
    # Context-dependent fields
    file = models.FileField(upload_to='materials/', null=True, blank=True)
    content = models.TextField(null=True, blank=True, help_text="Notes or External URL")
    
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.title} ({self.get_material_type_display()}) - {self.batch.name}"
        
    def filename(self):
        return os.path.basename(self.file.name) if self.file else ""

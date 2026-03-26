from django.db import models
from accounts.models import User
from batches.models import Batch

class CertificationApplication(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = 'PENDING', 'Pending Admin Approval'
        APPROVED = 'APPROVED', 'Approved by Admin'
        REJECTED = 'REJECTED', 'Rejected'

    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'STUDENT'}, related_name='certifications')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='certifications')
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)

    # Applicant Demographics & Details
    full_name = models.CharField(max_length=255, null=True, blank=False)
    fathers_name = models.CharField(max_length=255, null=True, blank=False)
    mothers_name = models.CharField(max_length=255, null=True, blank=False)
    date_of_birth = models.DateField(null=True, blank=False)
    email_id = models.EmailField(null=True, blank=False)
    contact_number = models.CharField(max_length=15, null=True, blank=False)
    
    # Academic Details
    course_start_date = models.DateField(null=True, blank=False)
    course_end_date = models.DateField(null=True, blank=False)
    
    class CategoryChoices(models.TextChoices):
        GENERAL = 'GENERAL', 'General'
        OBC = 'OBC', 'OBC'
        SC = 'SC', 'SC'
        ST = 'ST', 'ST'
        OTHER = 'OTHER', 'Other'
    
    caste_category = models.CharField(max_length=20, choices=CategoryChoices.choices, null=True, blank=False)
    
    class EducationChoices(models.TextChoices):
        TENTH = '10TH', '10th Standard'
        TWELFTH = '12TH', '12th Standard'
        UG = 'UG', 'Undergraduate'
        PG = 'PG', 'Postgraduate'
        DIPLOMA = 'DIPLOMA', 'Diploma'
        OTHER = 'OTHER', 'Other'
        
    highest_education = models.CharField(max_length=20, choices=EducationChoices.choices, null=True, blank=False)
    address_with_pincode = models.TextField(null=True, blank=False)
    
    # Media
    passport_photo = models.ImageField(upload_to='certification_photos/', null=True, blank=False)

    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'batch')

    def __str__(self):
        return f"Certification App: {self.student.username} for {self.batch.name} ({self.get_status_display()})"

import uuid
from courses.models import Course

def generate_cert_id():
    return uuid.uuid4().hex[:12].upper()

class Certificate(models.Model):
    application = models.OneToOneField(CertificationApplication, on_delete=models.CASCADE, related_name='certificate')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='awarded_certificates')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    certificate_id = models.CharField(max_length=20, default=generate_cert_id, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Certificate {self.certificate_id} - {self.student.username}"

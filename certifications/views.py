from django.views.generic import ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from enrollments.models import Enrollment
from batches.models import Batch
from recommendations.models import Recommendation
from .models import CertificationApplication, Certificate
from .forms import CertificationApplicationForm
from courses.models import Course

class StudentRequiredMixin(UserPassesTestMixin):
    raise_exception = True
    def test_func(self):
        return self.request.user.is_authenticated and getattr(self.request.user, 'role', '') == 'STUDENT'

class AdminRequiredMixin(UserPassesTestMixin):
    raise_exception = True
    def test_func(self):
        return self.request.user.is_authenticated and getattr(self.request.user, 'role', '') == 'ADMIN'

class StudentCertificationListView(LoginRequiredMixin, StudentRequiredMixin, ListView):
    model = Enrollment
    template_name = 'certifications/student_certification_list.html'
    context_object_name = 'enrollments'

    def get_queryset(self):
        return Enrollment.objects.filter(student=self.request.user).select_related('batch')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        enrollments = context['enrollments']
        cert_data = []
        for e in enrollments:
            batch = e.batch
            recommendation = Recommendation.objects.filter(student=self.request.user, batch=batch).first()
            application = CertificationApplication.objects.filter(student=self.request.user, batch=batch).first()
            cert_data.append({
                'enrollment': e,
                'is_recommended': recommendation is not None,
                'application': application
            })
        context['cert_data'] = cert_data
        context['pending_count'] = sum(1 for item in cert_data if item['application'] and item['application'].status == 'PENDING')
        context['approved_count'] = sum(1 for item in cert_data if item['application'] and item['application'].status == 'APPROVED')
        context['rejected_count'] = sum(1 for item in cert_data if item['application'] and item['application'].status == 'REJECTED')
        return context

class ApplyCertificationView(LoginRequiredMixin, StudentRequiredMixin, View):
    def get(self, request, batch_id):
        student = request.user
        batch = get_object_or_404(Batch, pk=batch_id)
        
        # Validation checks before allowing the form to render
        if not Enrollment.has_module_access(student, batch):
            messages.error(request, 'You are not enrolled in this batch.')
            return redirect('student_certification_list')
        if not Recommendation.objects.filter(student=student, batch=batch).exists():
            messages.error(request, 'You must be recommended by your trainer before applying.')
            return redirect('student_certification_list')
        if CertificationApplication.objects.filter(student=student, batch=batch).exists():
            messages.info(request, 'You have already applied for this certification.')
            return redirect('student_certification_list')
            
        form = CertificationApplicationForm(initial={
            'full_name': f"{student.first_name} {student.last_name}".strip() or student.username,
            'email_id': student.email
        })
        return render(request, 'certifications/apply_certification.html', {'form': form, 'batch': batch})

    def post(self, request, batch_id):
        student = request.user
        batch = get_object_or_404(Batch, pk=batch_id)
        
        # Double check validation on post
        if not Recommendation.objects.filter(student=student, batch=batch).exists():
            messages.error(request, 'Unauthorized. Trainer recommendation required.')
            return redirect('student_certification_list')
            
        if CertificationApplication.objects.filter(student=student, batch=batch).exists():
            messages.info(request, 'Application already exists.')
            return redirect('student_certification_list')
            
        form = CertificationApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.student = student
            application.batch = batch
            application.save()
            messages.success(request, f'Successfully submitted your certification application for {batch.name}!')
            return redirect('student_certification_list')
            
        return render(request, 'certifications/apply_certification.html', {'form': form, 'batch': batch})

# --- Admin Views --- #

class AdminApplicationListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = CertificationApplication
    template_name = 'certifications/admin_application_list.html'
    context_object_name = 'applications'
    
    def get_queryset(self):
        # Order by pending first, then oldest
        return CertificationApplication.objects.all().order_by('status', 'applied_at')

class AdminApproveApplicationView(LoginRequiredMixin, AdminRequiredMixin, View):
    def post(self, request, app_id):
        application = get_object_or_404(CertificationApplication, pk=app_id)
        
        if application.status != 'PENDING':
            messages.error(request, 'Application is no longer pending.')
            return redirect('admin_application_list')
            
        # 1. Update status
        application.status = 'APPROVED'
        application.save()
        
        # 2. Update Trainer Recommendation status to match
        recommendation = Recommendation.objects.filter(student=application.student, batch=application.batch).first()
        if recommendation:
            recommendation.status = 'APPROVED'
            recommendation.save()
            
        # 3. Generate Certificate
        Certificate.objects.create(
            application=application,
            student=application.student,
            course=application.batch.course,
            batch=application.batch
        )
        
        messages.success(request, f"Approved! Certificate generated for {application.student.username}.")
        return redirect('admin_application_list')

class AdminRejectApplicationView(LoginRequiredMixin, AdminRequiredMixin, View):
    def post(self, request, app_id):
        application = get_object_or_404(CertificationApplication, pk=app_id)
        
        if application.status != 'PENDING':
            messages.error(request, 'Application is no longer pending.')
            return redirect('admin_application_list')
            
        # 1. Update status
        application.status = 'REJECTED'
        application.save()
        
        # 2. Update Trainer Recommendation status to match
        recommendation = Recommendation.objects.filter(student=application.student, batch=application.batch).first()
        if recommendation:
            recommendation.status = 'REJECTED'
            recommendation.save()
            
        messages.warning(request, f"Application rejected for {application.student.username}.")
        return redirect('admin_application_list')

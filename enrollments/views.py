from django.views.generic import CreateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from .models import Enrollment
from .forms import EnrollmentForm
from accounts.models import User

class StudentRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and getattr(self.request.user, 'role', '') == User.Role.STUDENT


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and getattr(self.request.user, 'role', '') == User.Role.ADMIN


class EnrollmentCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Enrollment
    form_class = EnrollmentForm
    template_name = 'enrollments/enrollment_form.html'
    success_url = reverse_lazy('adminpanel_enrollments')

    def form_valid(self, form):
        student = form.cleaned_data['student']
        batch = form.cleaned_data['batch']
        module = form.cleaned_data.get('module')

        if Enrollment.objects.filter(student=student, batch=batch, module=module).exists():
            messages.error(self.request, "This enrollment already exists.")
            return self.form_invalid(form)

        messages.success(self.request, "Enrollment created successfully.")
        return super().form_valid(form)


class StudentEnrollmentListView(LoginRequiredMixin, StudentRequiredMixin, ListView):
    model = Enrollment
    template_name = 'enrollments/enrollment_list.html'
    context_object_name = 'enrollments'

    def get_queryset(self):
        return Enrollment.objects.filter(student=self.request.user).select_related('batch', 'course', 'module', 'batch__trainer')

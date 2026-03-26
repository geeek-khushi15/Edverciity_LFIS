from django.views.generic import ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from enrollments.models import Enrollment
from batches.models import Batch
from accounts.models import User
from assessments.models import TestAttempt, Test
from .models import Recommendation

class TrainerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and getattr(self.request.user, 'role', '') == 'TRAINER'

class StudentPerformanceListView(LoginRequiredMixin, TrainerRequiredMixin, ListView):
    model = Enrollment
    template_name = 'recommendations/student_performance_list.html'
    context_object_name = 'enrollments'

    def get_queryset(self):
        # trainer only sees students in their batches
        trainer = self.request.user
        trainer_batches = Batch.objects.filter(trainer=trainer)
        return Enrollment.objects.filter(batch__in=trainer_batches).select_related('student', 'batch')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # We need to enrich context with testing data and existing recommendations
        enrollments = context['enrollments']
        performance_data = []
        
        for e in enrollments:
            student = e.student
            batch = e.batch
            
            # Find tests associated with this batch
            batch_tests = Test.objects.filter(batch=batch)
            total_tests = batch_tests.count()
            
            # Find attempts by this student for these tests
            attempts = TestAttempt.objects.filter(student=student, test__in=batch_tests)
            tests_attempted = attempts.count()
            tests_passed = len([a for a in attempts if a.is_passed])
            
            # Find if recommendation already exists
            recommendation = Recommendation.objects.filter(student=student, batch=batch).first()
            
            performance_data.append({
                'enrollment': e,
                'total_tests': total_tests,
                'tests_attempted': tests_attempted,
                'tests_passed': tests_passed,
                'recommendation': recommendation
            })
            
        context['performance_data'] = performance_data
        return context

class RecommendStudentView(LoginRequiredMixin, TrainerRequiredMixin, View):
    def post(self, request, student_id, batch_id):
        student = get_object_or_404(User, pk=student_id, role='STUDENT')
        batch = get_object_or_404(Batch, pk=batch_id)
        
        # Verify trainer owns batch
        if batch.trainer != request.user:
            messages.error(request, 'Unauthorized action.')
            return redirect('student_performance_list')
            
        # Verify student is logically enrolled
        if not Enrollment.has_module_access(student, batch):
            messages.error(request, 'Student is not formally enrolled in this batch.')
            return redirect('student_performance_list')
            
        # Verify not already explicitly recommended
        if Recommendation.objects.filter(student=student, batch=batch).exists():
            messages.info(request, 'Recommendation already submitted.')
            return redirect('student_performance_list')
            
        Recommendation.objects.create(
            student=student,
            batch=batch,
            recommended_by=request.user
        )
        messages.success(request, f'Successfully recommended {student.username} for certification!')
        return redirect('student_performance_list')

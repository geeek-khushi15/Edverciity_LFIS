from django.views.generic import CreateView, ListView, DetailView, View, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.db.models import Count
from django.db.models import Q
from django.utils import timezone

from .models import Test, Question, TestAttempt, Assignment, AssignmentSubmission
from enrollments.models import Enrollment
from .forms import (
    TestForm,
    QuestionForm,
    AssignmentForm,
    AssignmentSubmissionForm,
    AssignmentEvaluationForm,
)


class TrainerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and getattr(self.request.user, 'role', '') == 'TRAINER'


class StudentRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and getattr(self.request.user, 'role', '') == 'STUDENT'


class AssignmentCreateView(LoginRequiredMixin, TrainerRequiredMixin, CreateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'assessments/assignment_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['trainer'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.trainer = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        messages.success(self.request, 'Assignment created successfully.')
        return reverse('trainer_assignment_list')


class AssignmentUpdateView(LoginRequiredMixin, TrainerRequiredMixin, UpdateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'assessments/assignment_form.html'

    def get_queryset(self):
        return Assignment.objects.filter(trainer=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['trainer'] = self.request.user
        return kwargs

    def get_success_url(self):
        messages.success(self.request, 'Assignment updated successfully.')
        return reverse('trainer_assignment_list')


class AssignmentDeleteView(LoginRequiredMixin, TrainerRequiredMixin, DeleteView):
    model = Assignment
    template_name = 'assessments/assignment_confirm_delete.html'

    def get_queryset(self):
        return Assignment.objects.filter(trainer=self.request.user)

    def get_success_url(self):
        messages.success(self.request, 'Assignment deleted successfully.')
        return reverse('trainer_assignment_list')


class TrainerAssignmentListView(LoginRequiredMixin, TrainerRequiredMixin, ListView):
    model = Assignment
    template_name = 'assessments/trainer_assignment_list.html'
    context_object_name = 'assignments'

    def get_queryset(self):
        return Assignment.objects.filter(
            trainer=self.request.user
        ).select_related('course', 'batch').annotate(
            submission_count=Count('submissions', distinct=True)
        ).order_by('-created_at')


class TrainerAssignmentSubmissionListView(LoginRequiredMixin, TrainerRequiredMixin, DetailView):
    model = Assignment
    template_name = 'assessments/trainer_assignment_submissions.html'
    context_object_name = 'assignment'

    def get_queryset(self):
        return Assignment.objects.filter(trainer=self.request.user).select_related('course', 'batch')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['submissions'] = self.object.submissions.select_related('student').order_by('-submitted_at')
        return context


class TrainerAllSubmissionListView(LoginRequiredMixin, TrainerRequiredMixin, ListView):
    model = AssignmentSubmission
    template_name = 'assessments/trainer_all_submissions.html'
    context_object_name = 'submissions'

    def get_queryset(self):
        return AssignmentSubmission.objects.filter(
            assignment__trainer=self.request.user
        ).select_related('assignment', 'assignment__batch', 'student').order_by('status', '-submitted_at')


class AssignmentSubmissionReviewView(LoginRequiredMixin, TrainerRequiredMixin, UpdateView):
    model = AssignmentSubmission
    form_class = AssignmentEvaluationForm
    template_name = 'assessments/review_submission.html'

    def get_queryset(self):
        return AssignmentSubmission.objects.filter(assignment__trainer=self.request.user).select_related(
            'assignment', 'student'
        )

    def form_valid(self, form):
        submission = form.save(commit=False)
        if submission.marks_obtained is not None:
            submission.status = AssignmentSubmission.Status.REVIEWED
        submission.save()
        messages.success(self.request, 'Submission evaluated successfully.')
        return redirect('trainer_assignment_submissions', pk=submission.assignment_id)


class StudentAssignmentListView(LoginRequiredMixin, StudentRequiredMixin, ListView):
    model = Assignment
    template_name = 'assessments/student_assignment_list.html'
    context_object_name = 'assignments'

    def get_queryset(self):
        enrollments = Enrollment.objects.filter(student=self.request.user)
        full_q = Q(batch_id__in=enrollments.filter(enrollment_type=Enrollment.EnrollmentType.FULL).values_list('batch_id', flat=True))
        module_pairs = enrollments.filter(enrollment_type=Enrollment.EnrollmentType.MODULE, module__isnull=False).values_list('batch_id', 'module_id')
        module_q = Q()
        for batch_id, module_id in module_pairs:
            module_q |= Q(batch_id=batch_id, module_id=module_id)

        return Assignment.objects.filter(full_q | module_q).select_related('course', 'module', 'batch', 'trainer').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        submissions = AssignmentSubmission.objects.filter(
            student=self.request.user,
            assignment__in=context['assignments']
        )
        submission_map = {submission.assignment_id: submission for submission in submissions}
        context['assignment_cards'] = [
            {
                'assignment': assignment,
                'submission': submission_map.get(assignment.id)
            }
            for assignment in context['assignments']
        ]
        return context


class AssignmentSubmitView(LoginRequiredMixin, StudentRequiredMixin, View):
    def get(self, request, assignment_id):
        assignment = get_object_or_404(Assignment, pk=assignment_id)

        is_enrolled = Enrollment.has_module_access(request.user, assignment.batch, assignment.module)
        if not is_enrolled:
            messages.error(request, 'You are not enrolled in this assignment batch.')
            return redirect('student_assignment_list')

        submission = AssignmentSubmission.objects.filter(
            assignment=assignment,
            student=request.user
        ).first()

        form = AssignmentSubmissionForm(instance=submission)

        return render(request, 'assessments/assignment_submit.html', {
            'assignment': assignment,
            'form': form,
            'submission': submission,
        })

    def post(self, request, assignment_id):
        assignment = get_object_or_404(Assignment, pk=assignment_id)

        is_enrolled = Enrollment.has_module_access(request.user, assignment.batch, assignment.module)
        if not is_enrolled:
            messages.error(request, 'You are not enrolled in this assignment batch.')
            return redirect('student_assignment_list')

        submission = AssignmentSubmission.objects.filter(
            assignment=assignment,
            student=request.user
        ).first()

        form = AssignmentSubmissionForm(request.POST, request.FILES, instance=submission)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.assignment = assignment
            submission.student = request.user
            submission.status = AssignmentSubmission.Status.PENDING
            submission.submitted_at = timezone.now()
            submission.save()
            messages.success(request, 'Assignment submitted successfully.')
            return redirect('student_assignment_list')

        return render(request, 'assessments/assignment_submit.html', {
            'assignment': assignment,
            'form': form,
            'submission': submission,
        })


class TestCreateView(LoginRequiredMixin, TrainerRequiredMixin, CreateView):
    model = Test
    form_class = TestForm
    template_name = 'assessments/test_form.html'

    def get_success_url(self):
        return reverse('test_detail', kwargs={'pk': self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['trainer'] = self.request.user
        return kwargs

    def form_valid(self, form):
        test = form.save(commit=False)
        test.trainer = self.request.user
        if not test.course_id and test.batch_id:
            test.course = test.batch.course
        test.save()
        messages.success(self.request, 'Test created successfully.')
        return redirect('test_detail', pk=test.pk)


class TestDetailView(LoginRequiredMixin, TrainerRequiredMixin, DetailView):
    model = Test
    template_name = 'assessments/test_detail.html'
    context_object_name = 'test'

    def get_queryset(self):
        return Test.objects.filter(
            Q(trainer=self.request.user) | Q(batch__trainer=self.request.user)
        ).select_related('batch', 'course')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['questions'] = self.object.questions.all()
        return context


class TrainerTestListView(LoginRequiredMixin, TrainerRequiredMixin, ListView):
    model = Test
    template_name = 'assessments/trainer_test_list.html'
    context_object_name = 'tests'

    def get_queryset(self):
        return Test.objects.filter(
            Q(trainer=self.request.user) | Q(batch__trainer=self.request.user)
        ).select_related('batch', 'course').annotate(
            questions_total=Count('questions', distinct=True),
            attempt_count=Count('attempts', distinct=True)
        ).order_by('-created_at')


class TrainerTestResultsView(LoginRequiredMixin, TrainerRequiredMixin, ListView):
    model = TestAttempt
    template_name = 'assessments/trainer_test_results.html'
    context_object_name = 'attempts'

    def get_queryset(self):
        queryset = TestAttempt.objects.filter(
            Q(test__trainer=self.request.user) | Q(test__batch__trainer=self.request.user)
        ).select_related('student', 'test', 'test__batch').order_by('-submitted_at', '-attempted_at')

        test_id = self.request.GET.get('test')
        if test_id:
            queryset = queryset.filter(test_id=test_id)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tests'] = Test.objects.filter(
            Q(trainer=self.request.user) | Q(batch__trainer=self.request.user)
        ).distinct().order_by('-created_at')
        context['selected_test'] = self.request.GET.get('test', '')
        return context


class QuestionCreateView(LoginRequiredMixin, TrainerRequiredMixin, CreateView):
    model = Question
    form_class = QuestionForm
    template_name = 'assessments/question_form.html'

    def form_valid(self, form):
        test = get_object_or_404(
            Test,
            Q(pk=self.kwargs['test_id']) & (Q(trainer=self.request.user) | Q(batch__trainer=self.request.user))
        )
        question = form.save(commit=False)
        question.test = test

        # Keep backward-compatible fields in sync with new field names.
        question.text = question.question_text
        question.option1 = question.option_a
        question.option2 = question.option_b
        question.option3 = question.option_c
        question.option4 = question.option_d
        option_map = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
        question.correct_option = option_map.get(question.correct_answer, 1)
        question.save()

        messages.success(self.request, 'Question added successfully.')
        return redirect('test_detail', pk=test.pk)

    def get_success_url(self):
        return reverse('test_detail', kwargs={'pk': self.kwargs['test_id']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['test'] = get_object_or_404(
            Test,
            Q(pk=self.kwargs['test_id']) & (Q(trainer=self.request.user) | Q(batch__trainer=self.request.user))
        )
        return context


class StudentTestListView(LoginRequiredMixin, StudentRequiredMixin, ListView):
    model = Test
    template_name = 'assessments/student_test_list.html'
    context_object_name = 'tests'

    def get_queryset(self):
        enrollments = Enrollment.objects.filter(student=self.request.user)
        full_q = Q(batch_id__in=enrollments.filter(enrollment_type=Enrollment.EnrollmentType.FULL).values_list('batch_id', flat=True))
        module_pairs = enrollments.filter(enrollment_type=Enrollment.EnrollmentType.MODULE, module__isnull=False).values_list('batch_id', 'module_id')
        module_q = Q()
        for batch_id, module_id in module_pairs:
            module_q |= Q(batch_id=batch_id, module_id=module_id)

        return Test.objects.filter(full_q | module_q).select_related('batch', 'course', 'module').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        attempted_tests = TestAttempt.objects.filter(student=self.request.user).values_list('test_id', flat=True)
        context['attempted_test_ids'] = list(attempted_tests)

        completed_attempts = TestAttempt.objects.filter(
            student=self.request.user
        ).select_related('test', 'test__batch').order_by('-submitted_at', '-attempted_at')

        context['completed_attempts'] = completed_attempts[:6]
        context['avg_score'] = round(
            (sum(a.score for a in completed_attempts) / completed_attempts.count()) if completed_attempts else 0,
            1
        )
        return context


class TestAttemptView(LoginRequiredMixin, StudentRequiredMixin, View):
    def get(self, request, test_id):
        test = get_object_or_404(Test, pk=test_id)

        if not Enrollment.has_module_access(request.user, test.batch, test.module):
            messages.error(request, 'You are not enrolled in the batch for this test.')
            return redirect('dashboard')

        if TestAttempt.objects.filter(student=request.user, test=test).exists():
            messages.info(request, 'You have already attempted this test.')
            return redirect('student_test_list')

        now = timezone.now()
        if test.start_time and now < test.start_time:
            messages.error(request, 'This test has not started yet.')
            return redirect('student_test_list')
        if test.end_time and now > test.end_time:
            messages.error(request, 'This test window has ended.')
            return redirect('student_test_list')

        questions = test.questions.all()
        return render(request, 'assessments/test_attempt.html', {'test': test, 'questions': questions})

    def post(self, request, test_id):
        test = get_object_or_404(Test, pk=test_id)

        if not Enrollment.has_module_access(request.user, test.batch, test.module):
            return redirect('student_test_list')
        if TestAttempt.objects.filter(student=request.user, test=test).exists():
            return redirect('student_test_list')

        now = timezone.now()
        if test.start_time and now < test.start_time:
            messages.error(request, 'This test has not started yet.')
            return redirect('student_test_list')
        if test.end_time and now > test.end_time:
            messages.error(request, 'This test window has ended.')
            return redirect('student_test_list')

        score = 0
        questions = test.questions.all()

        for question in questions:
            selected_option = request.POST.get(f'question_{question.id}')
            if not selected_option:
                continue
            if int(selected_option) == question.correct_option:
                score += 1

        TestAttempt.objects.create(
            student=request.user,
            test=test,
            score=score,
            submitted_at=timezone.now(),
        )

        messages.success(request, f'Test submitted. Your score: {score}/{questions.count()}')
        return redirect('student_test_list')

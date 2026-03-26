from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.urls import reverse
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Avg, Count, Q
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import csv
import re

from .forms import StudentRegistrationForm, TrainerRegistrationForm, StudentDoubtForm, TrainerProfileForm
from .models import User, TrainerProfile, EmployeeAttendanceLog, StudentProfile, StudentDoubt

from enrollments.models import Enrollment
from batches.models import Batch
from assessments.models import Test, TestAttempt
from courses.models import Course, CourseModule, TopicProgress
from certifications.models import CertificationApplication, Certificate
from attendance.models import ClassSession, SessionTopic, AttendanceRecord


# ===============================
# STUDENT REGISTRATION
# ===============================

def student_register(request):
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Create empty profile automatically
            StudentProfile.objects.get_or_create(user=user)

            login(request, user)
            return redirect('dashboard')
    else:
        form = StudentRegistrationForm()

    return render(request, 'accounts/register_student.html', {'form': form})


# ===============================
# TRAINER REGISTRATION
# ===============================

def trainer_register(request):
    if request.method == 'POST':
        form = TrainerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = TrainerRegistrationForm()

    return render(request, 'accounts/register_trainer.html', {'form': form})


# ===============================
# LOGIN
# ===============================

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('dashboard')


# ===============================
# LOGOUT
# ===============================

def custom_logout(request):
    logout(request)
    return redirect('login')


# ===============================
# DASHBOARD
# ===============================

@login_required
def dashboard(request):

    if request.user.role == 'STUDENT':

        student_enrollments = Enrollment.objects.filter(student=request.user).select_related('course', 'module', 'batch')
        enrollments_count = student_enrollments.count()
        pending_doubts_count = StudentDoubt.objects.filter(
            student=request.user,
            status=StudentDoubt.Status.PENDING
        ).count()
        resolved_doubts_count = StudentDoubt.objects.filter(
            student=request.user,
            status=StudentDoubt.Status.RESOLVED
        ).count()
        upcoming_tests_count = Test.objects.filter(
            batch__enrollments__student=request.user
        ).exclude(
            attempts__student=request.user
        ).count()
        tests_completed_count = TestAttempt.objects.filter(student=request.user).count()
        certificates_earned_count = Certificate.objects.filter(student=request.user).count()

        total_topics = TopicProgress.objects.filter(
            student=request.user,
        ).values('topic').distinct().count()
        acknowledged_topics = TopicProgress.objects.filter(
            student=request.user,
            student_marked_understood=True,
        ).values('topic').distinct().count()
        pending_acknowledgements_count = max(total_topics - acknowledged_topics, 0)

        purchased_cards = []
        full_course_ids = set(student_enrollments.filter(enrollment_type=Enrollment.EnrollmentType.FULL).values_list('course_id', flat=True).distinct())
        full_course_modules = {
            module.course_id: []
            for module in CourseModule.objects.filter(course_id__in=full_course_ids).order_by('order_number', 'id')
        }
        for module in CourseModule.objects.filter(course_id__in=full_course_ids).order_by('order_number', 'id'):
            full_course_modules.setdefault(module.course_id, []).append(module)

        for enrollment in student_enrollments.order_by('-enrollment_date'):
            if enrollment.enrollment_type == Enrollment.EnrollmentType.FULL:
                purchased_cards.append({
                    'type': 'FULL',
                    'title': enrollment.course.title,
                    'modules': full_course_modules.get(enrollment.course_id, []),
                    'batch': enrollment.batch,
                })
            elif enrollment.module:
                purchased_cards.append({
                    'type': 'MODULE',
                    'title': enrollment.module.name,
                    'modules': [],
                    'batch': enrollment.batch,
                })

        return render(request, 'accounts/student_dashboard.html', {
            'enrollments_count': enrollments_count,
            'pending_doubts_count': pending_doubts_count,
            'resolved_doubts_count': resolved_doubts_count,
            'upcoming_tests_count': upcoming_tests_count,
            'pending_acknowledgements_count': pending_acknowledgements_count,
            'tests_completed_count': tests_completed_count,
            'certificates_earned_count': certificates_earned_count,
            'purchased_cards': purchased_cards,
        })


    elif request.user.role == 'TRAINER':

        batches = Batch.objects.filter(
            trainer=request.user
        ).select_related('course')

        trainer_enrollments = Enrollment.objects.filter(
            batch__trainer=request.user
        ).select_related('student', 'batch__course')

        enrolled_students_count = trainer_enrollments.values('student').distinct().count()

        trainer_pending_doubts_count = StudentDoubt.objects.filter(
            student__enrollments__batch__trainer=request.user,
            status=StudentDoubt.Status.PENDING
        ).distinct().count()

        attendance_days_this_month = EmployeeAttendanceLog.objects.filter(
            trainer=request.user,
            date__year=timezone.now().year,
            date__month=timezone.now().month
        ).count()

        hierarchy_rows = []
        hierarchy_map = {}
        trainer_enrollment_rows = Enrollment.objects.filter(batch__trainer=request.user).select_related('course', 'module', 'batch').order_by('course__title', 'module__order_number', 'batch__name')
        for enrollment in trainer_enrollment_rows:
            course_key = enrollment.course_id
            if course_key not in hierarchy_map:
                hierarchy_map[course_key] = {
                    'course': enrollment.course,
                    'modules': {},
                }
                hierarchy_rows.append(hierarchy_map[course_key])

            module_name = enrollment.module.name if enrollment.module else 'Full Course'
            if module_name not in hierarchy_map[course_key]['modules']:
                hierarchy_map[course_key]['modules'][module_name] = set()
            hierarchy_map[course_key]['modules'][module_name].add(enrollment.batch.name)

        trainer_hierarchy = []
        for item in hierarchy_rows:
            module_rows = [
                {
                    'module_name': module_name,
                    'batches': sorted(list(batch_names)),
                }
                for module_name, batch_names in item['modules'].items()
            ]
            trainer_hierarchy.append({'course': item['course'], 'module_rows': module_rows})

        return render(request, 'accounts/trainer_dashboard.html', {
            'batches': batches,
            'enrolled_students_count': enrolled_students_count,
            'trainer_pending_doubts_count': trainer_pending_doubts_count,
            'attendance_days_this_month': attendance_days_this_month,
            'trainer_hierarchy': trainer_hierarchy,
        })

    elif request.user.role == 'SUPERADMIN':
        return redirect('/secure-admin/')

    elif request.user.role == 'ADMIN':
        return redirect('adminpanel_dashboard')

    else:
        admin_pending_doubts_count = StudentDoubt.objects.filter(
            status=StudentDoubt.Status.PENDING
        ).count()

        return render(request, 'accounts/admin_dashboard.html', {
            'admin_pending_doubts_count': admin_pending_doubts_count,
            'total_students': User.objects.filter(role=User.Role.STUDENT).count(),
            'total_trainers': User.objects.filter(role=User.Role.TRAINER).count(),
            'courses_running': Course.objects.count(),
            'pending_certifications': CertificationApplication.objects.filter(
                status=CertificationApplication.StatusChoices.PENDING
            ).count(),
        })


# ===============================
# LANDING PAGE
# ===============================

class LandingPageView(TemplateView):
    template_name = 'accounts/landing_page.html'


@login_required
def trainer_doubts(request):
    if request.user.role != User.Role.TRAINER:
        return redirect('dashboard')

    trainer_doubts_qs = StudentDoubt.objects.filter(
        student__enrollments__batch__trainer=request.user
    ).distinct().select_related(
        'student',
        'related_course',
        'related_session',
        'trainer'
    )

    if request.method == 'POST' and request.POST.get('action') in {'trainer_reply', 'trainer_resolve'}:
        doubt = get_object_or_404(
            trainer_doubts_qs,
            id=request.POST.get('doubt_id')
        )

        response_text = request.POST.get('response', '').strip()

        if response_text:
            doubt.response = response_text

        doubt.trainer = request.user

        if request.POST.get('action') == 'trainer_resolve':
            doubt.status = StudentDoubt.Status.RESOLVED
            doubt.resolved_at = timezone.now()

        doubt.save()
        return redirect('trainer_doubts')

    trainer_pending_doubts = trainer_doubts_qs.filter(status=StudentDoubt.Status.PENDING)
    trainer_resolved_doubts = trainer_doubts_qs.filter(status=StudentDoubt.Status.RESOLVED)[:20]

    return render(request, 'accounts/trainer_doubts.html', {
        'trainer_pending_doubts': trainer_pending_doubts,
        'trainer_resolved_doubts': trainer_resolved_doubts,
    })


@login_required
def trainer_batch_report(request):
    if request.user.role != User.Role.TRAINER:
        return redirect('dashboard')

    batches = Batch.objects.filter(trainer=request.user).select_related('course').order_by('name')
    selected_batch_id = request.GET.get('batch', '').strip()

    selected_batch = None
    report = None

    if selected_batch_id:
        selected_batch = get_object_or_404(batches, id=selected_batch_id)

        enrollments = Enrollment.objects.filter(batch=selected_batch).select_related('student', 'student__studentprofile').order_by('student__first_name', 'student__username')
        students = [enrollment.student for enrollment in enrollments]

        attendance_qs = AttendanceRecord.objects.filter(
            session__batch=selected_batch,
            session__trainer=request.user,
        )

        total_attendance_sessions = attendance_qs.values('session_id').distinct().count()

        attendance_summary_qs = attendance_qs.values('student_id').annotate(
            present_count=Count('id', filter=Q(status=AttendanceRecord.Status.PRESENT)),
            absent_count=Count('id', filter=Q(status=AttendanceRecord.Status.ABSENT)),
        )
        attendance_summary_by_student = {
            row['student_id']: row for row in attendance_summary_qs
        }

        student_rows = []
        for student in students:
            try:
                student_profile = student.studentprofile
            except StudentProfile.DoesNotExist:
                student_profile = None

            profile_name = (student_profile.full_name or '').strip() if student_profile else ''
            user_full_name = (student.get_full_name() or '').strip()
            student_display_name = profile_name or user_full_name or student.username

            summary = attendance_summary_by_student.get(student.id, {})
            present_count = summary.get('present_count', 0)
            absent_count = summary.get('absent_count', 0)
            attendance_percent = round((present_count / total_attendance_sessions) * 100, 1) if total_attendance_sessions else 0

            student_rows.append({
                'student': student,
                'student_display_name': student_display_name,
                'present_count': present_count,
                'absent_count': absent_count,
                'attendance_percent': attendance_percent,
            })

        detailed_attendance_records = AttendanceRecord.objects.filter(
            session__batch=selected_batch,
            session__trainer=request.user,
        ).select_related('student', 'session').order_by('-session__session_date', 'student__first_name', 'student__username')

        class_sessions = ClassSession.objects.filter(
            batch=selected_batch,
            trainer=request.user,
        ).prefetch_related('topics').order_by('-date', '-created_at')

        topic_names = set(
            SessionTopic.objects.filter(
                session__in=class_sessions,
                trainer_taught=True,
            ).values_list('topic_name', flat=True)
        )

        for session in class_sessions:
            if session.topics_covered:
                for item in re.split(r'[\n,]+', session.topics_covered):
                    cleaned = item.strip()
                    if cleaned:
                        topic_names.add(cleaned)

        sorted_topics = sorted(topic_names)
        latest_session = class_sessions.first()

        report = {
            'batch': selected_batch,
            'course': selected_batch.course,
            'student_count': len(students),
            'student_rows': student_rows,
            'total_attendance_sessions': total_attendance_sessions,
            'class_session_count': class_sessions.count(),
            'latest_session_date': latest_session.date if latest_session else None,
            'topics': sorted_topics,
            'topics_count': len(sorted_topics),
            'detailed_attendance_records': list(detailed_attendance_records),
        }

        if request.GET.get('export') == 'csv':
            filename = f"batch_report_{selected_batch.name}_{timezone.now().date()}".replace(' ', '_')
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'

            writer = csv.writer(response)
            writer.writerow(['Batch Report'])
            writer.writerow(['Batch Name', selected_batch.name])
            writer.writerow(['Course', selected_batch.course.title])
            writer.writerow(['Trainer', request.user.get_full_name() or request.user.username])
            writer.writerow(['Batch Start Date', selected_batch.start_date])
            writer.writerow(['Batch End Date', selected_batch.end_date])
            writer.writerow(['Total Students', report['student_count']])
            writer.writerow(['Attendance Sessions Marked', report['total_attendance_sessions']])
            writer.writerow(['Class Sessions Logged', report['class_session_count']])
            writer.writerow(['Latest Session Date', report['latest_session_date'] or '-'])
            writer.writerow([])

            writer.writerow(['Student Attendance Summary'])
            writer.writerow(['Student Name', 'Username', 'Email', 'Present', 'Absent', 'Attendance %'])
            for row in report['student_rows']:
                student = row['student']
                writer.writerow([
                    row['student_display_name'],
                    student.username,
                    student.email,
                    row['present_count'],
                    row['absent_count'],
                    row['attendance_percent'],
                ])

            writer.writerow([])
            writer.writerow(['Detailed Attendance Records'])
            writer.writerow(['Date', 'Student Name', 'Status'])
            for record in report['detailed_attendance_records']:
                student = record.student
                try:
                    student_profile = student.studentprofile
                except StudentProfile.DoesNotExist:
                    student_profile = None
                profile_name = (student_profile.full_name or '').strip() if student_profile else ''
                user_full_name = (student.get_full_name() or '').strip()
                student_display_name = profile_name or user_full_name or student.username
                writer.writerow([
                    record.session.session_date,
                    student_display_name,
                    record.status,
                ])

            writer.writerow([])
            writer.writerow(['Topics Covered'])
            if report['topics']:
                for topic in report['topics']:
                    writer.writerow([topic])
            else:
                writer.writerow(['No topics marked yet'])

            return response

    return render(
        request,
        'accounts/trainer_batch_report.html',
        {
            'batches': batches,
            'selected_batch_id': selected_batch_id,
            'report': report,
        }
    )


@login_required
def admin_doubts(request):
    if request.user.role not in {User.Role.ADMIN, 'ADMIN'}:
        return redirect('dashboard')

    admin_doubts_qs = StudentDoubt.objects.select_related(
        'student',
        'trainer',
        'related_course',
        'related_session'
    )

    if request.method == 'POST' and request.POST.get('action') in {'admin_reply', 'admin_resolve'}:
        doubt = get_object_or_404(admin_doubts_qs, id=request.POST.get('doubt_id'))

        response_text = request.POST.get('response', '').strip()
        if response_text:
            doubt.response = response_text

        if request.POST.get('action') == 'admin_resolve':
            doubt.status = StudentDoubt.Status.RESOLVED
            doubt.resolved_at = timezone.now()

        doubt.save()
        return redirect('admin_doubts')

    admin_pending_doubts = admin_doubts_qs.filter(status=StudentDoubt.Status.PENDING)
    admin_resolved_doubts = admin_doubts_qs.filter(status=StudentDoubt.Status.RESOLVED)[:20]

    return render(request, 'accounts/admin_doubts.html', {
        'admin_pending_doubts': admin_pending_doubts,
        'admin_resolved_doubts': admin_resolved_doubts,
    })


@login_required
def student_raise_doubt(request):
    if request.user.role != User.Role.STUDENT:
        return redirect('dashboard')

    if request.method == 'POST':
        doubt_form = StudentDoubtForm(request.POST, student=request.user)

        if doubt_form.is_valid():
            doubt = doubt_form.save(commit=False)
            doubt.student = request.user

            query_type = doubt_form.cleaned_data.get('query_type')
            query_tags = {
                'subject_topic': 'Subject/Topic',
                'soft_skill': 'Soft Skill',
                'placement': 'Placement',
            }
            if query_type in query_tags:
                doubt.title = f"[{query_tags[query_type]}] {doubt.title}"

            if doubt.related_session and not doubt.related_course:
                doubt.related_course = doubt.related_session.batch.course

            if doubt.related_session and doubt.related_session.trainer:
                doubt.trainer = doubt.related_session.trainer
            elif doubt.related_course:
                first_enrollment = Enrollment.objects.filter(
                    student=request.user,
                    batch__course=doubt.related_course
                ).select_related('batch__trainer').first()

                if first_enrollment:
                    doubt.trainer = first_enrollment.batch.trainer

            doubt.save()
            return redirect('student_raise_doubt')
    else:
        doubt_form = StudentDoubtForm(student=request.user)

    submitted_doubts = StudentDoubt.objects.filter(
        student=request.user,
        status=StudentDoubt.Status.PENDING
    ).select_related('related_course', 'related_session', 'trainer')

    resolved_doubts = StudentDoubt.objects.filter(
        student=request.user,
        status=StudentDoubt.Status.RESOLVED
    ).select_related('related_course', 'related_session', 'trainer')

    return render(request, 'accounts/student_raise_doubt.html', {
        'doubt_form': doubt_form,
        'submitted_doubts': submitted_doubts,
        'resolved_doubts': resolved_doubts,
    })


# ===============================
# ROLE MIXINS
# ===============================

class StudentRequiredMixin(UserPassesTestMixin):

    raise_exception = True

    def test_func(self):
        return (
            self.request.user.is_authenticated and
            getattr(self.request.user, 'role', '') == 'STUDENT'
        )


class TrainerRequiredMixin(UserPassesTestMixin):

    raise_exception = True

    def test_func(self):
        return (
            self.request.user.is_authenticated and
            getattr(self.request.user, 'role', '') == 'TRAINER'
        )


# ===============================
# STUDENT PROFILE VIEW
# ===============================

class StudentProfileView(LoginRequiredMixin, StudentRequiredMixin, TemplateView):

    template_name = 'accounts/student_profile.html'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        # Fetch enrollments
        enrollments = Enrollment.objects.filter(
            student=self.request.user
        ).select_related('batch', 'batch__course')
        context['enrollments'] = enrollments

        # Fetch or create profile
        profile, created = StudentProfile.objects.get_or_create(
            user=self.request.user
        )

        context['profile'] = profile

        return context


class StudentProgressView(LoginRequiredMixin, StudentRequiredMixin, TemplateView):

    template_name = 'accounts/student_progress.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        enrollments = Enrollment.objects.filter(
            student=self.request.user
        ).select_related('batch', 'batch__course')

        student_progress_chart = []
        for enrollment in enrollments:
            total_tests = enrollment.batch.tests.count()
            attempted_tests = TestAttempt.objects.filter(
                student=self.request.user,
                test__batch=enrollment.batch
            ).count()

            progress = int((attempted_tests / total_tests) * 100) if total_tests else 0

            student_progress_chart.append({
                'course': enrollment.batch.course.title,
                'batch': enrollment.batch.name,
                'progress': progress,
            })

        context['student_progress_chart'] = student_progress_chart
        context['chart_labels'] = [f"{item['course']} ({item['batch']})" for item in student_progress_chart]
        context['chart_values'] = [item['progress'] for item in student_progress_chart]

        return context


# ===============================
# TRAINER PROFILE
# ===============================

class TrainerProfileView(LoginRequiredMixin, TrainerRequiredMixin, TemplateView):

    template_name = 'accounts/trainer_profile.html'

    def post(self, request, *args, **kwargs):
        trainer_profile, _ = TrainerProfile.objects.get_or_create(user=request.user)
        form = TrainerProfileForm(request.POST, request.FILES, instance=trainer_profile)

        if form.is_valid():
            form.save()
            messages.success(request, 'Trainer profile updated successfully.')
            return redirect('trainer_profile')

        messages.error(request, 'Please correct the highlighted errors and try again.')
        context = self.get_context_data(**kwargs)
        context['trainer_form'] = form
        context['edit_mode'] = True
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        batches = Batch.objects.filter(
            trainer=self.request.user
        ).select_related('course')

        trainer_profile, _ = TrainerProfile.objects.get_or_create(user=self.request.user)

        courses_handled = batches.values('course_id').distinct().count()
        total_batches = batches.count()

        trainer_enrollments = Enrollment.objects.filter(
            batch__trainer=self.request.user
        ).select_related('student', 'batch', 'batch__course')
        students_trained = trainer_enrollments.values('student_id').distinct().count()

        completed_sessions = ClassSession.objects.filter(trainer=self.request.user).count()

        avg_score_data = TestAttempt.objects.filter(
            test__batch__trainer=self.request.user
        ).aggregate(avg_score=Avg('score'))
        average_test_score = round(avg_score_data['avg_score'] or 0, 1)

        assigned_course_titles = list(
            batches.values_list('course__title', flat=True).distinct()
        )

        domain_value = getattr(trainer_profile, 'department', None)
        if not domain_value:
            domain_value = assigned_course_titles[0] if assigned_course_titles else '-'

        context['trainer_profile_data'] = {
            'full_name': trainer_profile.full_name or self.request.user.get_full_name() or self.request.user.username,
            'email': self.request.user.email,
            'role_badge': 'Active Trainer',
            'department_domain': domain_value,
            'years_of_experience': getattr(trainer_profile, 'years_of_experience', None) or '-',
            'father_name': getattr(trainer_profile, 'father_name', None) or '-',
            'date_of_birth': getattr(trainer_profile, 'date_of_birth', None) or '-',
            'gender': getattr(trainer_profile, 'gender', None) or '-',
            'contact_number': getattr(trainer_profile, 'contact_number', None) or '-',
            'address': getattr(trainer_profile, 'address', None) or '-',
            'pincode': getattr(trainer_profile, 'pincode', None) or '-',
            'trainer_id': getattr(trainer_profile, 'trainer_id', None) or f"TRN-{self.request.user.id:04d}",
            'highest_education': getattr(trainer_profile, 'highest_education', None) or '-',
            'specialization': getattr(trainer_profile, 'specialization', None) or '-',
            'profile_photo': trainer_profile.profile_photo,
        }

        context['batches'] = batches
        context['courses_assigned'] = assigned_course_titles
        context['session_schedules'] = list(
            batches.values_list('name', 'start_date', 'end_date')[:6]
        )

        context['trainer_stats'] = {
            'courses_handled': courses_handled,
            'total_batches': total_batches,
            'students_trained': students_trained,
            'total_courses': courses_handled,
            'total_students': students_trained,
            'completed_sessions': completed_sessions,
            'average_test_score': average_test_score,
        }

        context['edit_mode'] = self.request.GET.get('edit') == '1'
        context.setdefault('trainer_form', TrainerProfileForm(instance=trainer_profile))

        return context


# ===============================
# TRAINER FACE SETUP
# ===============================

def trainer_setup_face(request):

    trainer_id = request.session.get('pending_trainer_id')

    if not trainer_id:
        return redirect('login')

    try:
        trainer = User.objects.get(id=trainer_id, role='TRAINER')
    except User.DoesNotExist:
        return redirect('login')

    return render(request, 'accounts/trainer_setup_face.html', {
        'trainer': trainer
    })


# ===============================
# EMPLOYEE FACE LOGIN
# ===============================

@login_required
def employee_verification(request):

    if request.user.role != 'TRAINER':
        return redirect('dashboard')

    try:
        profile = TrainerProfile.objects.get(user=request.user)
    except TrainerProfile.DoesNotExist:
        return redirect('dashboard')

    if not profile.is_setup_complete or not profile.face_descriptor:
        return redirect('trainer_setup_face')

    from datetime import date

    already_logged_in = EmployeeAttendanceLog.objects.filter(
        trainer=request.user,
        date=date.today()
    ).exists()

    if already_logged_in:
        return redirect('dashboard')

    return render(request, 'accounts/employee_verification.html', {
        'trainer': request.user,
        'saved_descriptor': profile.face_descriptor
    })


# ===============================
# FACE API
# ===============================

import json

@csrf_exempt
def api_employee_verification(request):

    if request.method == 'POST':

        try:

            data = json.loads(request.body)

            action = data.get('action')

            user_auth = request.user if request.user.is_authenticated else None

            trainer_id = request.session.get('pending_trainer_id')

            if not user_auth and not trainer_id:
                return JsonResponse({'success': False})

            trainer = user_auth if user_auth else User.objects.get(id=trainer_id)

            if action == 'register_face':

                descriptor = data.get('descriptor')

                profile = TrainerProfile.objects.get(user=trainer)

                profile.face_descriptor = json.dumps(descriptor)

                profile.is_setup_complete = True

                profile.save()

                return JsonResponse({'success': True})

            elif action == 'verify_face':

                status = data.get('status') == 'success'

                lat = data.get('lat')
                lng = data.get('lng')

                if status:

                    from datetime import date

                    log, created = EmployeeAttendanceLog.objects.get_or_create(
                        trainer=trainer,
                        date=date.today(),
                        defaults={
                            'login_time': timezone.now().time(),
                            'latitude': lat,
                            'longitude': lng,
                            'face_verified': True
                        }
                    )

                    if not created:
                        return JsonResponse({'success': False})

                    return JsonResponse({'success': True})

        except Exception as e:

            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False})


# ===============================
# CHECKOUT API
# ===============================

@login_required
@csrf_exempt
def api_employee_checkout(request):

    if request.method == 'POST':

        if request.user.role != 'TRAINER':
            return JsonResponse({'success': False})

        from datetime import date

        try:

            today_log = EmployeeAttendanceLog.objects.get(
                trainer=request.user,
                date=date.today()
            )

            if today_log.logout_time:
                return JsonResponse({'success': False})

            today_log.logout_time = timezone.now().time()

            today_log.save()

            return JsonResponse({'success': True})

        except EmployeeAttendanceLog.DoesNotExist:

            return JsonResponse({'success': False})

    return JsonResponse({'success': False})
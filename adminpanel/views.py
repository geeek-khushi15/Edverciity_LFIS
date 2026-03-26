from functools import wraps

from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import render, redirect
from django.utils import timezone

from accounts.forms import AdminStudentProfileCreateForm, AdminTrainerProfileCreateForm
from accounts.models import User, StudentDoubt
from assessments.models import Assignment, AssignmentSubmission, Test, TestAttempt
from attendance.models import AttendanceSession, AttendanceRecord
from batches.models import Batch
from certifications.models import CertificationApplication, Certificate
from courses.models import Course, CourseModule, CourseTopic
from courses.forms import TopicsImportForm
from courses.utils import import_topics_to_course, parse_csv_topics, parse_text_topics
from enrollments.models import Enrollment


# ─── Access Decorator ────────────────────────────────────────────────────────

def admin_required(view_func):
    """Redirect non-ADMIN users to the admin panel login."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('adminpanel_login')
        if getattr(request.user, 'role', '') != 'ADMIN':
            messages.error(request, 'Access restricted to Organisation Admins.')
            return redirect('adminpanel_login')
        return view_func(request, *args, **kwargs)
    return wrapper


# ─── Auth ─────────────────────────────────────────────────────────────────────

def adminpanel_login(request):
    if request.user.is_authenticated and getattr(request.user, 'role', '') == 'ADMIN':
        return redirect('adminpanel_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user and user.is_active and getattr(user, 'role', '') == 'ADMIN':
            login(request, user)
            return redirect('adminpanel_dashboard')
        messages.error(request, 'Invalid credentials or you do not have Admin access.')

    return render(request, 'adminpanel/login.html')


def adminpanel_logout(request):
    logout(request)
    return redirect('adminpanel_login')


# ─── Dashboard ────────────────────────────────────────────────────────────────

@admin_required
def adminpanel_dashboard(request):
    context = {
        'total_students': User.objects.filter(role='STUDENT').count(),
        'total_trainers': User.objects.filter(role='TRAINER').count(),
        'total_courses': Course.objects.count(),
        'total_modules': CourseModule.objects.count(),
        'total_topics': CourseTopic.objects.count(),
        'total_batches': Batch.objects.count(),
        'total_enrollments': Enrollment.objects.count(),
        'pending_doubts': StudentDoubt.objects.filter(status='PENDING').count(),
        'pending_certs': CertificationApplication.objects.filter(status='PENDING').count(),
        'total_assignments': Assignment.objects.count(),
        'total_tests': Test.objects.count(),
        'approved_certs': Certificate.objects.count(),
        'recent_enrollments': Enrollment.objects.select_related('student', 'course', 'batch')
                                              .order_by('-enrollment_date')[:5],
    }
    return render(request, 'adminpanel/dashboard.html', context)


# ─── Students ─────────────────────────────────────────────────────────────────

@admin_required
def adminpanel_students(request):
    q = request.GET.get('q', '').strip()
    students = User.objects.filter(role='STUDENT').annotate(
        enrollment_count=Count('enrollments', distinct=True),
        attempt_count=Count('test_attempts', distinct=True),
    ).order_by('username')
    if q:
        students = students.filter(
            Q(username__icontains=q) | Q(email__icontains=q)
            | Q(first_name__icontains=q) | Q(last_name__icontains=q)
        )
    return render(request, 'adminpanel/students.html', {'students': students, 'q': q})


@admin_required
def adminpanel_student_create(request):
    if request.method == 'POST':
        form = AdminStudentProfileCreateForm(request.POST, request.FILES)
        if form.is_valid():
            profile = form.save()
            messages.success(request, f'Student profile created for {profile.user.username}.')
            return redirect('adminpanel_students')
    else:
        form = AdminStudentProfileCreateForm()

    return render(request, 'adminpanel/student_create.html', {'form': form})


# ─── Trainers ─────────────────────────────────────────────────────────────────

@admin_required
def adminpanel_trainers(request):
    q = request.GET.get('q', '').strip()
    trainers = User.objects.filter(role='TRAINER').select_related('trainer_profile').annotate(
        batch_count=Count('trainer_batches', distinct=True),
    ).order_by('username')
    if q:
        trainers = trainers.filter(
            Q(username__icontains=q) | Q(email__icontains=q)
            | Q(first_name__icontains=q) | Q(last_name__icontains=q)
        )
    return render(request, 'adminpanel/trainers.html', {'trainers': trainers, 'q': q})


@admin_required
def adminpanel_trainer_create(request):
    if request.method == 'POST':
        form = AdminTrainerProfileCreateForm(request.POST, request.FILES)
        if form.is_valid():
            profile = form.save()
            messages.success(request, f'Trainer profile created for {profile.user.username}.')
            return redirect('adminpanel_trainers')
    else:
        form = AdminTrainerProfileCreateForm()

    return render(request, 'adminpanel/trainer_create.html', {'form': form})


# ─── Courses ──────────────────────────────────────────────────────────────────

@admin_required
def adminpanel_courses(request):
    courses = Course.objects.annotate(
        module_count=Count('modules', distinct=True),
        topic_count=Count('topics', distinct=True),
        batch_count=Count('batches', distinct=True),
        enrollment_count=Count('enrollments', distinct=True),
    ).order_by('title')
    return render(request, 'adminpanel/courses.html', {'courses': courses})


@admin_required
def adminpanel_topics(request):
    topics = list(CourseTopic.objects.select_related('course', 'module', 'created_by').order_by(
        'course__title', 'module__order_number', 'topic_number', 'id'
    ))

    courses_with_topics = []
    grouped_by_course = {}

    for topic in topics:
        course_id = topic.course_id
        if course_id not in grouped_by_course:
            grouped_by_course[course_id] = {
                'course': topic.course,
                'topics': [],
            }
            courses_with_topics.append(grouped_by_course[course_id])
        grouped_by_course[course_id]['topics'].append(topic)

    return render(request, 'adminpanel/topics.html', {
        'topics': topics,
        'courses_with_topics': courses_with_topics,
        'total_topics': len(topics),
    })


@admin_required
def adminpanel_topics_import(request):
    """Bulk import topics for a course from text or CSV"""
    if request.method == 'POST':
        form = TopicsImportForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.cleaned_data['course']
            import_method = form.cleaned_data['import_method']
            description = form.cleaned_data['description']
            start_topic_number = form.cleaned_data.get('start_topic_number')
            
            # Parse topics based on import method
            if import_method == 'text':
                topics_list = parse_text_topics(form.cleaned_data['topic_list'])
            else:  # CSV
                csv_file = request.FILES['csv_file']
                topics_list = parse_csv_topics(csv_file)
            
            if not topics_list:
                messages.error(request, 'No valid topics found in the provided input.')
                return render(request, 'adminpanel/topics_import.html', {'form': form})
            
            # Import topics
            result = import_topics_to_course(
                course,
                topics_list,
                description=description,
                start_number=start_topic_number
            )
            
            # Display results
            if result['imported'] > 0:
                messages.success(
                    request,
                    f"✓ Successfully imported {result['imported']} topics for '{course.title}'"
                )
            
            if result['skipped'] > 0:
                messages.warning(
                    request,
                    f"⊘ Skipped {result['skipped']} topics (already exist)"
                )
            
            if result['errors']:
                for error in result['errors'][:5]:
                    messages.error(request, f"✗ {error}")
                if len(result['errors']) > 5:
                    messages.error(request, f"... and {len(result['errors']) - 5} more errors")
            
            return redirect('adminpanel_topics')
    else:
        form = TopicsImportForm()
    
    return render(request, 'adminpanel/topics_import.html', {'form': form})


# ─── Modules ──────────────────────────────────────────────────────────────────

@admin_required
def adminpanel_modules(request):
    modules = CourseModule.objects.select_related('course').annotate(
        enrollment_count=Count('enrollments', distinct=True),
    ).order_by('course__title', 'order_number')
    return render(request, 'adminpanel/modules.html', {'modules': modules})


# ─── Batches ──────────────────────────────────────────────────────────────────

@admin_required
def adminpanel_batches(request):
    batches = Batch.objects.select_related('course', 'module', 'trainer').annotate(
        enrolled_count=Count('enrollments', distinct=True),
    ).order_by('name')
    return render(request, 'adminpanel/batches.html', {'batches': batches})


# ─── Enrollments ──────────────────────────────────────────────────────────────

@admin_required
def adminpanel_enrollments(request):
    enroll_type = request.GET.get('type', '')
    enrollments = Enrollment.objects.select_related(
        'student', 'course', 'batch', 'module'
    ).order_by('-enrollment_date')
    if enroll_type:
        enrollments = enrollments.filter(enrollment_type=enroll_type)
    return render(request, 'adminpanel/enrollments.html', {
        'enrollments': enrollments,
        'enroll_type': enroll_type,
    })


# ─── Attendance ───────────────────────────────────────────────────────────────

@admin_required
def adminpanel_attendance(request):
    sessions = AttendanceSession.objects.select_related(
        'batch', 'batch__course', 'trainer', 'module'
    ).annotate(
        record_count=Count('records', distinct=True),
    ).order_by('-session_date')[:200]
    return render(request, 'adminpanel/attendance.html', {'sessions': sessions})


# ─── Assignments ──────────────────────────────────────────────────────────────

@admin_required
def adminpanel_assignments(request):
    assignments = Assignment.objects.select_related('batch', 'batch__course', 'module').annotate(
        submission_count=Count('submissions', distinct=True),
    ).order_by('-due_date')
    return render(request, 'adminpanel/assignments.html', {'assignments': assignments})


# ─── Tests ────────────────────────────────────────────────────────────────────

@admin_required
def adminpanel_tests(request):
    tests = Test.objects.select_related('batch', 'batch__course', 'module').annotate(
        attempt_count=Count('attempts', distinct=True),
    ).order_by('-id')
    return render(request, 'adminpanel/tests.html', {'tests': tests})


# ─── Doubts ───────────────────────────────────────────────────────────────────

@admin_required
def adminpanel_doubts(request):
    status_filter = request.GET.get('status', '')
    doubts = StudentDoubt.objects.select_related('student', 'trainer').order_by('-created_at')
    if status_filter:
        doubts = doubts.filter(status=status_filter)
    counts = {
        'ALL': StudentDoubt.objects.count(),
        'PENDING': StudentDoubt.objects.filter(status='PENDING').count(),
        'RESOLVED': StudentDoubt.objects.filter(status='RESOLVED').count(),
    }
    return render(request, 'adminpanel/doubts.html', {
        'doubts': doubts,
        'status_filter': status_filter,
        'counts': counts,
    })


# ─── Certificates ─────────────────────────────────────────────────────────────

@admin_required
def adminpanel_certificates(request):
    status_filter = request.GET.get('status', '')
    applications = CertificationApplication.objects.select_related('student', 'batch').order_by('-applied_at')
    if status_filter:
        applications = applications.filter(status=status_filter)
    counts = {
        'PENDING': CertificationApplication.objects.filter(status='PENDING').count(),
        'APPROVED': CertificationApplication.objects.filter(status='APPROVED').count(),
        'REJECTED': CertificationApplication.objects.filter(status='REJECTED').count(),
    }
    return render(request, 'adminpanel/certificates.html', {
        'applications': applications,
        'status_filter': status_filter,
        'counts': counts,
    })


# ─── Reports ──────────────────────────────────────────────────────────────────

@admin_required
def adminpanel_reports(request):
    top_courses = Course.objects.annotate(
        enrollment_count=Count('enrollments', distinct=True)
    ).order_by('-enrollment_count')[:8]

    top_students = User.objects.filter(role='STUDENT').annotate(
        attempt_count=Count('test_attempts', distinct=True)
    ).order_by('-attempt_count')[:10]

    enrollment_by_type = {
        'FULL': Enrollment.objects.filter(enrollment_type='FULL').count(),
        'MODULE': Enrollment.objects.filter(enrollment_type='MODULE').count(),
    }

    monthly_enrollments = (
        Enrollment.objects
        .filter(enrollment_date__year=timezone.now().year)
        .extra(select={'month': "strftime('%%m', enrollment_date)"})
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

    context = {
        'top_courses': top_courses,
        'top_students': top_students,
        'enrollment_by_type': enrollment_by_type,
        'monthly_enrollments': list(monthly_enrollments),
        'total_revenue_proxies': {
            'full_enrollments': enrollment_by_type['FULL'],
            'module_enrollments': enrollment_by_type['MODULE'],
        },
    }
    return render(request, 'adminpanel/reports.html', context)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from django.urls import reverse

from .models import (
    ClassSession,
    Attendance,
    SessionTopic,
    TopicAcknowledgement,
    AttendanceSession,
    AttendanceRecord,
)
from batches.models import Batch
from enrollments.models import Enrollment
from courses.models import Course, CourseModule, CourseTopic, TopicProgress


def _status_from_checkbox(is_present):
    return Attendance.Status.PRESENT if is_present else Attendance.Status.ABSENT


@login_required
def create_session(request):
    if request.user.role != 'TRAINER':
        return redirect('dashboard')

    batches = Batch.objects.filter(trainer=request.user)

    if request.method == 'POST':
        batch_id = request.POST.get('batch')
        date = request.POST.get('date')
        topics_covered = request.POST.get('topics_covered', '').strip()

        batch = get_object_or_404(Batch, id=batch_id, trainer=request.user)

        # Create session
        session = ClassSession.objects.create(
            batch=batch,
            date=date,
            topics_covered=topics_covered,
            trainer=request.user
        )

        # Create attendance records
        enrollments = Enrollment.objects.filter(batch=batch)

        for enrollment in enrollments:
            Attendance.objects.get_or_create(
                session=session,
                student=enrollment.student,
                defaults={
                    'trainer': request.user,
                    'course': batch.course,
                    'batch': batch,
                    'session_date': session.date,
                    'status': Attendance.Status.PRESENT,
                    'is_present': True,
                }
            )

        # Parse topics
        if topics_covered:
            import re

            topic_list = [
                t.strip()
                for t in re.split(r'[,\n]+', topics_covered)
                if t.strip()
            ]

            for topic in topic_list:

                s_topic = SessionTopic.objects.create(
                    session=session,
                    topic_name=topic
                )

                for enrollment in enrollments:

                    TopicAcknowledgement.objects.get_or_create(
                        session_topic=s_topic,
                        student=enrollment.student
                    )

        messages.success(
            request,
            f"Class session and topics successfully logged for {batch.name}."
        )

        return redirect('trainer_session_list')

    return render(
        request,
        'attendance/create_session.html',
        {'batches': batches}
    )


@login_required
def mark_attendance(request, session_id):

    if request.user.role != 'TRAINER':
        return redirect('dashboard')

    session = get_object_or_404(
        ClassSession,
        id=session_id,
        trainer=request.user
    )

    attendances = session.attendances.all().select_related('student')

    if request.method == 'POST':

        for attendance in attendances:

            student_id = str(attendance.student.id)

            is_present = request.POST.get(
                f'attendance_{student_id}'
            ) == 'on'

            attendance.is_present = is_present
            attendance.status = _status_from_checkbox(is_present)
            attendance.trainer = request.user
            attendance.course = session.batch.course
            attendance.batch = session.batch
            attendance.session_date = session.date
            attendance.save()

        messages.success(
            request,
            f"Attendance successfully updated for {session.date}."
        )

        return redirect('trainer_session_list')

    return render(
        request,
        'attendance/mark_attendance.html',
        {
            'session': session,
            'attendances': attendances
        }
    )


@login_required
def trainer_session_list(request):

    if request.user.role != 'TRAINER':
        return redirect('dashboard')

    sessions = ClassSession.objects.filter(
        trainer=request.user
    ).select_related('batch').order_by('-date')

    return render(
        request,
        'attendance/trainer_session_list.html',
        {'sessions': sessions}
    )


@login_required
def manage_session_topics(request, session_id):

    if request.user.role != 'TRAINER':
        return redirect('dashboard')

    session = get_object_or_404(
        ClassSession,
        id=session_id,
        trainer=request.user
    )

    topics = session.topics.all()

    if request.method == 'POST':

        for topic in topics:

            if not topic.trainer_taught:

                topic_id = str(topic.id)

                taught = request.POST.get(
                    f'taught_{topic_id}'
                ) == 'on'

                if taught:
                    topic.trainer_taught = True
                    topic.taught_at = timezone.now()
                    topic.save()

        messages.success(
            request,
            f"Topics status updated for {session.date}."
        )

        return redirect('trainer_session_list')

    return render(
        request,
        'attendance/manage_session_topics.html',
        {
            'session': session,
            'topics': topics
        }
    )


@login_required
def student_session_list(request):

    if request.user.role != 'STUDENT':
        return redirect('dashboard')

    attendances = Attendance.objects.filter(
        student=request.user,
        is_present=True
    ).select_related(
        'session',
        'session__batch',
        'session__trainer'
    ).order_by('-session__date')

    sessions = [a.session for a in attendances]

    return render(
        request,
        'attendance/student_session_list.html',
        {'sessions': sessions}
    )


@login_required
def student_acknowledge_topics(request, session_id):

    if request.user.role != 'STUDENT':
        return redirect('dashboard')

    session = get_object_or_404(ClassSession, id=session_id)

    attendance = Attendance.objects.filter(
        session=session,
        student=request.user
    ).first()

    if not attendance or not attendance.is_present:

        messages.error(
            request,
            "You cannot view topics for a session you were marked absent from."
        )

        return redirect('student_session_list')

    acknowledgements = TopicAcknowledgement.objects.filter(
        session_topic__session=session,
        student=request.user
    ).select_related('session_topic')

    if request.method == 'POST':

        for ack in acknowledgements:

            ack_id = str(ack.id)

            understood = request.POST.get(
                f'understood_{ack_id}'
            ) == 'on'

            # IMPORTANT SECURITY CHECK
            # Student can acknowledge ONLY if trainer verified topic

            if (
                understood
                and not ack.student_understood
                and ack.session_topic.trainer_taught
            ):

                ack.student_understood = True
                ack.understood_at = timezone.now()
                ack.save()

        messages.success(
            request,
            "Topic acknowledgements successfully updated."
        )

        return redirect('student_session_list')

    return render(
        request,
        'attendance/student_acknowledge_topics.html',
        {
            'session': session,
            'acknowledgements': acknowledgements
        }
    )


@login_required
def trainer_attendance(request):
    if request.user.role != 'TRAINER':
        return redirect('dashboard')

    records = AttendanceRecord.objects.filter(
        session__trainer=request.user,
    ).select_related(
        'student',
        'module',
        'session',
        'session__topic',
        'session__course',
        'session__module',
        'session__batch',
    ).order_by('-session__session_date', 'student__username')[:40]

    return render(
        request,
        'attendance/trainer_attendance.html',
        {
            'records': records,
        }
    )


@login_required
def trainer_attendance_mark(request):
    if request.user.role != 'TRAINER':
        return redirect('dashboard')

    from datetime import date

    courses = Course.objects.filter(batches__trainer=request.user).distinct().order_by('title')
    selected_course_id = request.GET.get('course') or request.POST.get('course')
    selected_batch_id = request.GET.get('batch') or request.POST.get('batch')
    selected_module_id = request.GET.get('module') or request.POST.get('module')
    selected_topic_id = request.GET.get('topic') or request.POST.get('topic')
    selected_date = request.GET.get('date') or request.POST.get('session_date') or str(date.today())
    auto_selected_batch = False

    batches_qs = Batch.objects.filter(trainer=request.user).select_related('course').order_by('name')
    if selected_course_id:
        batches_qs = batches_qs.filter(course_id=selected_course_id)

        # If only course is chosen, auto-select the first batch so students load immediately.
        if not selected_batch_id:
            first_batch = batches_qs.first()
            if first_batch:
                selected_batch_id = str(first_batch.id)
                auto_selected_batch = True

    modules_qs = CourseModule.objects.none()
    topics_qs = CourseTopic.objects.none()
    if selected_course_id:
        modules_qs = CourseModule.objects.filter(course_id=selected_course_id).order_by('order_number', 'name')
        topics_qs = CourseTopic.objects.filter(course_id=selected_course_id).select_related('module').order_by('module__order_number', 'topic_number', 'id')
        if selected_module_id:
            topics_qs = topics_qs.filter(module_id=selected_module_id)

    selected_batch = None
    selected_module = None
    selected_topic = None
    enrollments = []
    student_rows = []
    existing_map = {}

    if selected_batch_id:
        selected_batch = get_object_or_404(
            Batch.objects.select_related('course'),
            id=selected_batch_id,
            trainer=request.user
        )

        if selected_module_id:
            selected_module = CourseModule.objects.filter(id=selected_module_id, course_id=selected_batch.course_id).first()

        if selected_topic_id:
            topic_qs = CourseTopic.objects.filter(id=selected_topic_id, course_id=selected_batch.course_id)
            if selected_module:
                topic_qs = topic_qs.filter(module=selected_module)
            selected_topic = topic_qs.first()

        if selected_batch.module_id:
            selected_module = selected_batch.module
            if topics_qs.exists():
                topics_qs = topics_qs.filter(module_id=selected_batch.module_id)
                if selected_topic and selected_topic.module_id != selected_batch.module_id:
                    selected_topic = None

        enrollments = Enrollment.objects.filter(batch=selected_batch).select_related('student').order_by('student__first_name', 'student__username')
        if selected_module:
            enrollments = enrollments.filter(
                Q(enrollment_type=Enrollment.EnrollmentType.FULL) |
                Q(enrollment_type=Enrollment.EnrollmentType.MODULE, module=selected_module)
            )

        existing_records = AttendanceRecord.objects.filter(
            session__batch=selected_batch,
            session__session_date=selected_date,
            session__module=selected_module,
            session__topic=selected_topic,
        ).select_related('student')
        existing_map = {record.student_id: record for record in existing_records}
        student_rows = [
            {
                'student': enrollment.student,
                'enrollment_id': enrollment.id,
                'existing': existing_map.get(enrollment.student.id),
            }
            for enrollment in enrollments
        ]

    if request.method == 'POST' and selected_batch:
        if not selected_topic:
            messages.error(request, 'Please select a topic for this session.')
            return redirect(
                f"{reverse('trainer_attendance_mark')}?course={selected_batch.course_id}&module={selected_module.id if selected_module else ''}&batch={selected_batch.id}&topic={selected_topic_id or ''}&date={selected_date}"
            )

        session, created = AttendanceSession.objects.get_or_create(
            batch=selected_batch,
            session_date=selected_date,
            topic=selected_topic,
            defaults={
                'course': selected_batch.course,
                'module': selected_module,
                'topic': selected_topic,
                'trainer': request.user,
            }
        )

        if not created and session.trainer_id != request.user.id:
            messages.error(request, 'Attendance for this batch and date is already created by another trainer.')
            return redirect(
                f"{reverse('trainer_attendance_mark')}?course={selected_batch.course_id}&batch={selected_batch.id}&date={selected_date}"
            )

        for enrollment in enrollments:
            student = enrollment.student
            selected_status = request.POST.get(f'status_{student.id}', AttendanceRecord.Status.PRESENT)
            if selected_status not in {AttendanceRecord.Status.PRESENT, AttendanceRecord.Status.ABSENT}:
                selected_status = AttendanceRecord.Status.PRESENT

            AttendanceRecord.objects.update_or_create(
                session=session,
                student=student,
                defaults={
                    'status': selected_status,
                    'module': selected_module,
                }
            )

            TopicProgress.objects.get_or_create(
                topic=selected_topic,
                student=student,
                trainer=request.user,
            )

        if created:
            messages.success(request, f'Attendance saved for {selected_batch.name} on {selected_date}.')
        else:
            messages.success(request, f'Attendance updated for {selected_batch.name} on {selected_date}.')
        return redirect(
            f"{reverse('trainer_attendance_mark')}?course={selected_batch.course_id}&module={selected_module.id if selected_module else ''}&batch={selected_batch.id}&topic={selected_topic.id if selected_topic else ''}&date={selected_date}"
        )

    return render(
        request,
        'attendance/trainer_attendance_mark.html',
        {
            'courses': courses,
            'batches': batches_qs,
            'modules': modules_qs,
            'selected_course_id': str(selected_course_id) if selected_course_id else '',
            'selected_module_id': str(selected_module_id) if selected_module_id else '',
            'selected_batch_id': str(selected_batch_id) if selected_batch_id else '',
            'selected_date': selected_date,
            'selected_batch': selected_batch,
            'selected_module': selected_module,
            'topics': topics_qs,
            'selected_topic_id': str(selected_topic_id) if selected_topic_id else '',
            'selected_topic': selected_topic,
            'student_rows': student_rows,
            'existing_map': existing_map,
            'auto_selected_batch': auto_selected_batch,
        }
    )


@login_required
def trainer_attendance_history(request):
    if request.user.role != 'TRAINER':
        return redirect('dashboard')

    batch_id = request.GET.get('batch', '')
    student_name = request.GET.get('student', '').strip()
    selected_batch = None
    missing_students = []

    records = AttendanceRecord.objects.filter(
        session__trainer=request.user,
    ).select_related(
        'student',
        'module',
        'session',
        'session__topic',
        'session__course',
        'session__module',
        'session__batch',
    ).order_by('-session__session_date', 'session__batch__name', 'student__username')

    if batch_id:
        records = records.filter(session__batch_id=batch_id)
        selected_batch = Batch.objects.filter(id=batch_id, trainer=request.user).select_related('course').first()

    if student_name:
        tokens = [token for token in student_name.split() if token]
        for token in tokens:
            records = records.filter(
                Q(student__username__icontains=token)
                | Q(student__first_name__icontains=token)
                | Q(student__last_name__icontains=token)
            )

    batches = Batch.objects.filter(trainer=request.user).order_by('name')

    return render(
        request,
        'attendance/trainer_attendance_history.html',
        {
            'records': records,
            'batches': batches,
            'selected_batch_id': batch_id,
            'selected_student': student_name,
            'selected_batch': selected_batch,
            'missing_students': missing_students,
        }
    )


@login_required
def student_attendance(request):
    if request.user.role != 'STUDENT':
        return redirect('dashboard')

    records = AttendanceRecord.objects.filter(
        student=request.user,
    ).select_related(
        'module',
        'session',
        'session__topic',
        'session__course',
        'session__module',
        'session__trainer',
        'session__batch',
    ).order_by('-session__session_date', '-marked_at')

    total = records.count()
    present = records.filter(status=AttendanceRecord.Status.PRESENT).count()
    percentage = round((present / total) * 100, 1) if total else 0

    course_summary = records.values('session__course__title').annotate(
        total_classes=Count('id'),
        present_classes=Count('id', filter=Q(status=AttendanceRecord.Status.PRESENT)),
    ).order_by('session__course__title')

    for item in course_summary:
        total_classes = item['total_classes'] or 0
        present_classes = item['present_classes'] or 0
        item['percentage'] = round((present_classes / total_classes) * 100, 1) if total_classes else 0

    return render(
        request,
        'attendance/student_attendance.html',
        {
            'records': records,
            'attendance_percentage': percentage,
            'total_classes': total,
            'present_classes': present,
            'course_summary': course_summary,
        }
    )
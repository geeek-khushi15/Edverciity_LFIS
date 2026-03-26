from django.views.generic import CreateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import redirect, render, get_object_or_404

from enrollments.models import Enrollment
from accounts.models import User

from .models import Course, CourseModule, CourseTopic, TopicProgress
from .forms import CourseForm
from attendance.models import ClassSession


def _bulk_create_topic_progress(progress_rows):
    if progress_rows:
        TopicProgress.objects.bulk_create(progress_rows, ignore_conflicts=True)


def _sync_topic_progress_for_topic(topic):
    enrollment_qs = Enrollment.objects.filter(course_id=topic.course_id).select_related('student', 'batch__trainer')
    if topic.module_id:
        enrollment_qs = enrollment_qs.filter(
            Q(enrollment_type=Enrollment.EnrollmentType.FULL)
            | Q(enrollment_type=Enrollment.EnrollmentType.MODULE, module_id=topic.module_id)
        )

    progress_rows = []
    for enrollment in enrollment_qs:
        trainer = enrollment.batch.trainer
        if not trainer or getattr(trainer, 'role', '') != User.Role.TRAINER:
            continue
        progress_rows.append(
            TopicProgress(
                topic=topic,
                student=enrollment.student,
                trainer=trainer,
            )
        )

    _bulk_create_topic_progress(progress_rows)


def _sync_topic_progress_for_enrollments(enrollment_qs):
    enrollments = list(enrollment_qs.select_related('student', 'batch__trainer'))
    if not enrollments:
        return

    course_ids = {enrollment.course_id for enrollment in enrollments if enrollment.course_id}
    if not course_ids:
        return

    topics_by_course = {}
    topics_by_module = {}
    topic_rows = CourseTopic.objects.filter(course_id__in=course_ids).values('id', 'course_id', 'module_id')
    for row in topic_rows:
        topics_by_course.setdefault(row['course_id'], []).append(row['id'])
        if row['module_id']:
            topics_by_module.setdefault((row['course_id'], row['module_id']), []).append(row['id'])

    progress_rows = []
    for enrollment in enrollments:
        trainer = enrollment.batch.trainer
        if not trainer or getattr(trainer, 'role', '') != User.Role.TRAINER:
            continue

        if enrollment.enrollment_type == Enrollment.EnrollmentType.MODULE and enrollment.module_id:
            topic_ids = topics_by_module.get((enrollment.course_id, enrollment.module_id), [])
        else:
            topic_ids = topics_by_course.get(enrollment.course_id, [])

        for topic_id in topic_ids:
            progress_rows.append(
                TopicProgress(
                    topic_id=topic_id,
                    student_id=enrollment.student_id,
                    trainer_id=trainer.id,
                )
            )

    _bulk_create_topic_progress(progress_rows)

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and getattr(self.request.user, 'role', '') == 'ADMIN'

    def handle_no_permission(self):
        return super().handle_no_permission()

class CourseCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    success_url = reverse_lazy('course_list')

class CourseListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'

    def test_func(self):
        return self.request.user.is_authenticated and getattr(self.request.user, 'role', '') in {'ADMIN', 'TRAINER'}

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            if getattr(self.request.user, 'role', '') == User.Role.STUDENT:
                return redirect('enrollment_list')
            return redirect('dashboard')
        return super().handle_no_permission()

    def get_queryset(self):
        queryset = Course.objects.all()
        if getattr(self.request.user, 'role', '') == User.Role.TRAINER:
            queryset = queryset.filter(batches__trainer=self.request.user).distinct()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        is_trainer = getattr(self.request.user, 'role', '') == User.Role.TRAINER

        course_cards = []
        for course in context['courses']:
            batches_qs = course.batches.select_related('trainer')
            if is_trainer:
                batches_qs = batches_qs.filter(trainer=self.request.user)
            batches = list(batches_qs)
            primary_batch = batches[0] if batches else None
            trainer_name = '-'

            if primary_batch and primary_batch.trainer:
                trainer_name = primary_batch.trainer.get_full_name() or primary_batch.trainer.username

            batch_ids = [b.id for b in batches]
            total_sessions = ClassSession.objects.filter(batch_id__in=batch_ids).count() if batch_ids else 0

            # Placeholder completion for management view cards.
            progress_percent = min(100, total_sessions * 5)

            course_cards.append({
                'course': course,
                'trainer_name': trainer_name,
                'batch_count': len(batches),
                'total_sessions': total_sessions,
                'progress_percent': progress_percent,
            })

        context['course_cards'] = course_cards
        return context


@login_required
def course_detail(request, course_id):
    role = getattr(request.user, 'role', '')
    if role not in {User.Role.ADMIN, User.Role.TRAINER}:
        if role == User.Role.STUDENT:
            return redirect('enrollment_list')
        return redirect('dashboard')

    course = get_object_or_404(Course, id=course_id)

    batches_qs = course.batches.select_related('trainer').prefetch_related('enrollments__student').order_by('name')
    if role == User.Role.TRAINER:
        batches_qs = batches_qs.filter(trainer=request.user)

    batch_cards = []
    total_students = 0

    for batch in batches_qs:
        enrollments = list(batch.enrollments.select_related('student').order_by('student__first_name', 'student__username'))
        students = [enrollment.student for enrollment in enrollments]
        student_count = len(students)
        total_students += student_count

        batch_cards.append({
            'batch': batch,
            'students': students,
            'student_count': student_count,
        })

    return render(
        request,
        'courses/course_detail.html',
        {
            'course': course,
            'batch_cards': batch_cards,
            'total_batches': len(batch_cards),
            'total_students': total_students,
        },
    )


@login_required
def course_topics_admin(request):
    if getattr(request.user, 'role', '') != User.Role.ADMIN:
        return redirect('dashboard')

    if request.method == 'POST':
        course_id = request.POST.get('course')
        module_id = request.POST.get('module')
        title = (request.POST.get('title') or '').strip()
        description = (request.POST.get('description') or '').strip()
        topic_number = request.POST.get('topic_number')
        resources_link = (request.POST.get('resources_link') or '').strip()

        if not (course_id and title and description and topic_number):
            messages.error(request, 'Please fill all required topic fields.')
            return redirect('course_topics_admin')

        try:
            topic_number = int(topic_number)
        except (TypeError, ValueError):
            messages.error(request, 'Topic number must be a valid number.')
            return redirect('course_topics_admin')

        course = Course.objects.filter(id=course_id).first()
        if not course:
            messages.error(request, 'Selected course was not found.')
            return redirect('course_topics_admin')

        module = None
        if module_id:
            module = CourseModule.objects.filter(id=module_id, course_id=course.id).first()
            if not module:
                messages.error(request, 'Selected module was not found for this course.')
                return redirect('course_topics_admin')

        topic = CourseTopic.objects.create(
            course=course,
            module=module,
            title=title,
            description=description,
            topic_number=topic_number,
            resources_link=resources_link or None,
            created_by=request.user,
        )
        _sync_topic_progress_for_topic(topic)
        messages.success(request, 'Course topic added successfully.')
        return redirect('course_topics_admin')

    topics = CourseTopic.objects.select_related('course', 'module', 'created_by').order_by('course__title', 'module__order_number', 'topic_number', 'id')
    courses = Course.objects.order_by('title')

    return render(
        request,
        'courses/course_topics_admin.html',
        {
            'topics': topics,
            'courses': courses,
        }
    )


@login_required
def topic_acknowledgement(request):
    if getattr(request.user, 'role', '') != User.Role.STUDENT:
        return redirect('dashboard')

    _sync_topic_progress_for_enrollments(Enrollment.objects.filter(student=request.user))

    student_progress_qs = TopicProgress.objects.filter(
        student=request.user,
        trainer__role=User.Role.TRAINER,
    ).select_related('topic', 'topic__course', 'topic__module', 'trainer')

    if request.method == 'POST':
        topic_id = request.POST.get('topic_id')
        progress = student_progress_qs.filter(topic_id=topic_id).first()

        if not progress:
            messages.error(request, 'This topic is not available for acknowledgement yet.')
            return redirect('topic_acknowledgement')

        if not progress.trainer_marked_taught:
            messages.error(request, 'Trainer must mark this topic as taught before you can acknowledge it.')
            return redirect('topic_acknowledgement')

        if not progress.student_marked_understood:
            progress.student_marked_understood = True
            progress.save(update_fields=['student_marked_understood', 'student_marked_at'])
            messages.success(request, f'You acknowledged: {progress.topic.title}')
        else:
            messages.info(request, f'{progress.topic.title} is already acknowledged.')

        return redirect('topic_acknowledgement')

    progress_records = list(student_progress_qs.order_by('topic__course__title', 'topic__module__order_number', 'topic__topic_number', 'topic__id'))
    topic_ids = [record.topic_id for record in progress_records]

    topic_total_students = {
        item['topic_id']: item['student_count']
        for item in TopicProgress.objects.filter(topic_id__in=topic_ids)
        .values('topic_id')
        .annotate(student_count=Count('student', distinct=True))
    }

    topic_understood_counts = {
        item['topic_id']: item['understood_count']
        for item in TopicProgress.objects.filter(topic_id__in=topic_ids, student_marked_understood=True)
        .values('topic_id')
        .annotate(understood_count=Count('student', distinct=True))
    }

    grouped = []
    grouped_map = {}
    for progress in progress_records:
        topic = progress.topic
        group_key = topic.module_id or topic.course_id
        if group_key not in grouped_map:
            grouped_map[group_key] = {
                'course': topic.course,
                'module': topic.module,
                'topics': [],
            }
            grouped.append(grouped_map[group_key])

        total_students = topic_total_students.get(topic.id, 0)
        understood_count = topic_understood_counts.get(topic.id, 0)
        coverage = int((understood_count / total_students) * 100) if total_students else 0

        grouped_map[group_key]['topics'].append({
            'topic': topic,
            'trainer_marked_taught': progress.trainer_marked_taught,
            'trainer_marked_at': progress.trainer_marked_at,
            'student_marked_understood': progress.student_marked_understood,
            'student_marked_at': progress.student_marked_at,
            'can_mark_understood': progress.trainer_marked_taught and not progress.student_marked_understood,
            'coverage_percent': coverage,
            'understood_count': understood_count,
            'total_students': total_students,
        })

    return render(
        request,
        'courses/topic_acknowledgement.html',
        {
            'course_groups': grouped,
        }
    )


@login_required
def trainer_topic_progress(request):
    if getattr(request.user, 'role', '') != User.Role.TRAINER:
        return redirect('dashboard')

    _sync_topic_progress_for_enrollments(Enrollment.objects.filter(batch__trainer=request.user))

    trainer_progress_qs = TopicProgress.objects.filter(trainer=request.user).select_related('topic', 'topic__course', 'topic__module', 'student')

    if request.method == 'POST':
        topic_id = request.POST.get('topic_id')
        progress_rows = trainer_progress_qs.filter(topic_id=topic_id)
        if not progress_rows.exists():
            messages.error(request, 'Invalid topic selected or no linked session yet.')
            return redirect('trainer_topic_progress')

        updates = 0
        for progress in progress_rows:
            if not progress.trainer_marked_taught:
                progress.trainer_marked_taught = True
                progress.save(update_fields=['trainer_marked_taught', 'trainer_marked_at'])
                updates += 1

        if updates:
            messages.success(request, f'Topic marked as taught for {updates} student record(s).')
        else:
            messages.info(request, 'This topic is already marked as taught.')

        return redirect('trainer_topic_progress')

    topic_ids = list(trainer_progress_qs.values_list('topic_id', flat=True).distinct())
    taught_topic_ids = set(
        trainer_progress_qs.filter(
            trainer_marked_taught=True,
        ).values_list('topic_id', flat=True)
    )

    grouped = []
    grouped_map = {}

    topics = CourseTopic.objects.filter(id__in=topic_ids).select_related('course', 'module').order_by('course__title', 'module__order_number', 'topic_number', 'id')

    for topic in topics:
        group_key = topic.module_id or topic.course_id
        if group_key not in grouped_map:
            grouped_map[group_key] = {
                'course': topic.course,
                'module': topic.module,
                'topic_rows': [],
            }
            grouped.append(grouped_map[group_key])

        topic_progress = trainer_progress_qs.filter(topic=topic)
        total_students = topic_progress.values('student').distinct().count()
        understood_students = topic_progress.filter(student_marked_understood=True).values('student').distinct().count()

        coverage = int((understood_students / total_students) * 100) if total_students else 0

        grouped_map[group_key]['topic_rows'].append({
            'topic': topic,
            'trainer_marked_taught': topic.id in taught_topic_ids,
            'students_understood': understood_students,
            'pending_students': max(total_students - understood_students, 0),
            'total_students': total_students,
            'coverage_percent': coverage,
        })

    return render(
        request,
        'courses/trainer_topic_progress.html',
        {
            'course_groups': grouped,
        }
    )

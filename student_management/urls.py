from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from attendance import views as attendance_views
from courses import views as course_views

def home(request):
    return redirect('/accounts/login/')

urlpatterns = [
    path('', home),
    path('login/', RedirectView.as_view(url='/accounts/login/', permanent=False), name='root_login'),
    path('secure-admin/course-topics/', course_views.course_topics_admin, name='course_topics_admin'),
    path('secure-admin/', admin.site.urls),
    path('admin-panel/', include('adminpanel.urls')),

    path('accounts/', include('accounts.urls')),
    path('attendance/', include('attendance.urls')),
    path('trainer/attendance/', attendance_views.trainer_attendance, name='trainer_attendance_top'),
    path('trainer/attendance/mark/', attendance_views.trainer_attendance_mark, name='trainer_attendance_mark_top'),
    path('trainer/attendance/history/', attendance_views.trainer_attendance_history, name='trainer_attendance_history_top'),
    path('student/attendance/', attendance_views.student_attendance, name='student_attendance_top'),

    path('', include('courses.urls')),
    path('', include('batches.urls')),
    path('', include('enrollments.urls')),
    path('', include('materials.urls')),
    path('', include('assessments.urls')),
    path('', include('recommendations.urls')),
    path('', include('certifications.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
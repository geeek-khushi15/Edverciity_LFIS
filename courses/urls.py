from django.urls import path
from . import views

urlpatterns = [
    path('courses/', views.CourseListView.as_view(), name='course_list'),
    path('courses/create/', views.CourseCreateView.as_view(), name='course_create'),
    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),
    path('student/topic-acknowledgement/', views.topic_acknowledgement, name='topic_acknowledgement'),
    path('trainer/topic-progress/', views.trainer_topic_progress, name='trainer_topic_progress'),
]

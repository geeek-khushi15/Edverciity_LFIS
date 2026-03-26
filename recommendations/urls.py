from django.urls import path
from . import views

urlpatterns = [
    path('performance/', views.StudentPerformanceListView.as_view(), name='student_performance_list'),
    path('recommend/<int:student_id>/<int:batch_id>/', views.RecommendStudentView.as_view(), name='recommend_student'),
]

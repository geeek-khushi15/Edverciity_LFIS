from django.urls import path
from . import views

urlpatterns = [
    # Trainer Assignments
    path('trainer/assignments/', views.TrainerAssignmentListView.as_view(), name='trainer_assignment_list'),
    path('trainer/assignments/create/', views.AssignmentCreateView.as_view(), name='assignment_create'),
    path('trainer/assignments/<int:pk>/edit/', views.AssignmentUpdateView.as_view(), name='assignment_edit'),
    path('trainer/assignments/<int:pk>/delete/', views.AssignmentDeleteView.as_view(), name='assignment_delete'),
    path('trainer/assignments/submissions/', views.TrainerAllSubmissionListView.as_view(), name='trainer_all_submissions'),
    path('trainer/assignments/<int:pk>/submissions/', views.TrainerAssignmentSubmissionListView.as_view(), name='trainer_assignment_submissions'),
    path('trainer/submissions/<int:pk>/review/', views.AssignmentSubmissionReviewView.as_view(), name='review_assignment_submission'),

    # Trainer Tests
    path('trainer/tests/', views.TrainerTestListView.as_view(), name='trainer_test_list'),
    path('trainer/tests/results/', views.TrainerTestResultsView.as_view(), name='trainer_test_results'),
    path('test/create/', views.TestCreateView.as_view(), name='test_create'),
    path('test/<int:pk>/', views.TestDetailView.as_view(), name='test_detail'),
    path('test/<int:test_id>/question/add/', views.QuestionCreateView.as_view(), name='question_create'),

    # Student Assignments
    path('student/assignments/', views.StudentAssignmentListView.as_view(), name='student_assignment_list'),
    path('student/assignments/<int:assignment_id>/submit/', views.AssignmentSubmitView.as_view(), name='assignment_submit'),

    # Student Tests
    path('tests/', views.StudentTestListView.as_view(), name='student_test_list'),
    path('test/<int:test_id>/attempt/', views.TestAttemptView.as_view(), name='test_attempt'),
]

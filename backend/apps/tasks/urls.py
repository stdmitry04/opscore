from django.urls import path
from .views import TaskListView, TaskDetailView, DeadLetterQueueView, RetryTaskView, TaskStreamView

urlpatterns = [
    path('', TaskListView.as_view()),
    path('stream/', TaskStreamView.as_view()),
    path('dlq/', DeadLetterQueueView.as_view()),
    path('<uuid:task_id>/', TaskDetailView.as_view()),
    path('<uuid:task_id>/retry/', RetryTaskView.as_view()),
]

from django.urls import path
from .views import ChatView, ClearSessionView

urlpatterns = [
    path('chat/', ChatView.as_view()),
    path('sessions/<str:session_id>/', ClearSessionView.as_view()),
]

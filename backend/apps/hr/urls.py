from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmployeeViewSet, JobViewSet, DocumentViewSet, AnalyticsView

router = DefaultRouter()
router.register('employees', EmployeeViewSet, basename='employee')
router.register('jobs', JobViewSet, basename='job')
router.register('documents', DocumentViewSet, basename='document')

urlpatterns = [
    path('', include(router.urls)),
    path('analytics/', AnalyticsView.as_view()),
]

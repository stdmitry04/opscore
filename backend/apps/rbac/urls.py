from django.urls import path
from .views import PermissionsView, RolesView, MyPermissionsView, TogglePermissionView

urlpatterns = [
    path('permissions/', PermissionsView.as_view()),
    path('roles/', RolesView.as_view()),
    path('roles/<uuid:role_id>/toggle/', TogglePermissionView.as_view()),
    path('me/', MyPermissionsView.as_view()),
]

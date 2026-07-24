from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
    path('api/auth/', include('apps.core.auth_urls')),
    path('api/hr/', include('apps.hr.urls')),
    path('api/agent/', include('apps.agent.urls')),
    path('api/tasks/', include('apps.tasks.urls')),
    path('api/rbac/', include('apps.rbac.urls')),
    path('api/health/', include('apps.core.health_urls')),
]

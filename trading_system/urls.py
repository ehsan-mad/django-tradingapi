from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),  # DRF login/logout
    path('api/', include('api.urls')),                  # all versioned API endpoints
    path('', include('signals.urls')),                  # webhook at root level
    path('health/', lambda r: HttpResponse('OK')),
]
from django.urls import path, include

urlpatterns = [
    path('v1/', include('signals.urls')),
    path('v1/', include('orders.urls')),
    path('v1/', include('brokers.urls')),
]

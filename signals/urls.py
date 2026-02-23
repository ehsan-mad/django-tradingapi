from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SignalWebhookView, TradingSignalViewSet

router = DefaultRouter()
router.register(r'signals', TradingSignalViewSet, basename='signals')

urlpatterns = [
    path('api/v1/', include(router.urls)),
    path('webhook/receive-signal/', SignalWebhookView.as_view(), name='webhook-receive-signal'),
]
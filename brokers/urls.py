from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import BrokerAccountViewSet

router = DefaultRouter()
router.register(r'broker-accounts', BrokerAccountViewSet, basename='broker-accounts')

urlpatterns = [
    path('', include(router.urls)),
]

import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

from .models import Order
from .serializers import (
    OrderSerializer,
    OrderCreateSerializer,
    OrderStatusUpdateSerializer,
)

logger = logging.getLogger(__name__)


class OrderViewSet(viewsets.ModelViewSet):
    """
    Manage trading orders.

    GET    /api/v1/orders/                      - list all your orders
    POST   /api/v1/orders/                      - create order from a valid signal
    GET    /api/v1/orders/{id}/                 - retrieve a single order
    POST   /api/v1/orders/{id}/update_status/   - update order status
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return orders belonging to the current user only"""
        return (
            Order.objects
            .filter(signal__user=self.request.user)
            .select_related('signal', 'broker_account')
            .order_by('-created_at')
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        if self.action == 'update_status':
            return OrderStatusUpdateSerializer
        return OrderSerializer

    def create(self, request, *args, **kwargs) -> Response:
        serializer = OrderCreateSerializer(
            data=request.data,
            context={'request': request}
        )

        if not serializer.is_valid():
            return Response(
                {
                    'status': 'error',
                    'errors': serializer.errors,
                    'message': 'Invalid order data',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        order = serializer.save()

        logger.info(
            "Order created: %s | signal=%s | user=%s",
            order.order_id,
            order.signal.instrument,
            request.user.username,
        )

        return Response(
            {
                'status': 'success',
                'message': 'Order created successfully',
                'data': OrderSerializer(order).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def list(self, request, *args, **kwargs) -> Response:
        queryset   = self.get_queryset()
        serializer = OrderSerializer(queryset, many=True)

        return Response(
            {
                'status': 'success',
                'message': f'{queryset.count()} order(s) found',
                'data': serializer.data,
            }
        )

    def retrieve(self, request, *args, **kwargs) -> Response:
        order      = self.get_object()
        serializer = OrderSerializer(order)

        return Response(
            {
                'status': 'success',
                'message': 'Order retrieved',
                'data': serializer.data,
            }
        )

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None) -> Response:
        """
        Update the status of an order.

        POST /api/v1/orders/{id}/update_status/

        Fields:
            status          - pending | executed | closed | cancelled
            executed_price  - required when status is 'executed'
        """
        order      = self.get_object()
        serializer = OrderStatusUpdateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    'status': 'error',
                    'errors': serializer.errors,
                    'message': 'Invalid status update',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_status     = serializer.validated_data['status']
        executed_price = serializer.validated_data.get('executed_price')

        # Update order fields
        order.status = new_status

        if new_status == Order.STATUS_EXECUTED:
            order.executed_price = executed_price
            order.executed_at    = timezone.now()

        order.save()

        logger.info(
            "Order %s status updated to %s | user=%s",
            order.order_id,
            new_status,
            request.user.username,
        )

        return Response(
            {
                'status': 'success',
                'message': f'Order status updated to {new_status}',
                'data': OrderSerializer(order).data,
            }
        )
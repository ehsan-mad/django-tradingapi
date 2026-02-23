import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import BrokerAccount
from .serializers import (
    BrokerAccountSerializer,
    BrokerAccountCreateSerializer,
    BrokerAccountUpdateSerializer,
)

logger = logging.getLogger(__name__)


class BrokerAccountViewSet(viewsets.ModelViewSet):
    """
    Manage broker accounts.

    GET    /api/v1/broker-accounts/              - list your broker accounts
    POST   /api/v1/broker-accounts/              - add a new broker account
    GET    /api/v1/broker-accounts/{id}/         - retrieve a single account
    PATCH  /api/v1/broker-accounts/{id}/         - update account details
    DELETE /api/v1/broker-accounts/{id}/         - remove a broker account
    POST   /api/v1/broker-accounts/{id}/toggle_active/ - activate or deactivate
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return broker accounts belonging to the current user only"""
        return (
            BrokerAccount.objects
            .filter(user=self.request.user)
            .order_by('-created_at')
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return BrokerAccountCreateSerializer
        if self.action in ('update', 'partial_update'):
            return BrokerAccountUpdateSerializer
        return BrokerAccountSerializer

    def create(self, request, *args, **kwargs) -> Response:
        serializer = BrokerAccountCreateSerializer(
            data=request.data,
            context={'request': request}
        )

        if not serializer.is_valid():
            return Response(
                {
                    'status': 'error',
                    'errors': serializer.errors,
                    'message': 'Invalid broker account data',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        account = serializer.save()

        logger.info(
            "Broker account created: %s | account_id=%s | user=%s",
            account.broker_name,
            account.account_id,
            request.user.username,
        )

        return Response(
            {
                'status': 'success',
                'message': 'Broker account added successfully',
                'data': BrokerAccountSerializer(account).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def list(self, request, *args, **kwargs) -> Response:
        queryset   = self.get_queryset()
        serializer = BrokerAccountSerializer(queryset, many=True)

        return Response(
            {
                'status': 'success',
                'message': f'{queryset.count()} broker account(s) found',
                'data': serializer.data,
            }
        )

    def retrieve(self, request, *args, **kwargs) -> Response:
        account    = self.get_object()
        serializer = BrokerAccountSerializer(account)

        return Response(
            {
                'status': 'success',
                'message': 'Broker account retrieved',
                'data': serializer.data,
            }
        )

    def update(self, request, *args, **kwargs) -> Response:
        account    = self.get_object()
        serializer = BrokerAccountUpdateSerializer(
            account,
            data=request.data,
            partial=kwargs.pop('partial', False),
        )

        if not serializer.is_valid():
            return Response(
                {
                    'status': 'error',
                    'errors': serializer.errors,
                    'message': 'Invalid update data',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        account = serializer.save()

        return Response(
            {
                'status': 'success',
                'message': 'Broker account updated',
                'data': BrokerAccountSerializer(account).data,
            }
        )

    def destroy(self, request, *args, **kwargs) -> Response:
        account = self.get_object()
        broker  = account.broker_name
        acct_id = account.account_id
        account.delete()

        logger.info(
            "Broker account deleted: %s | account_id=%s | user=%s",
            broker,
            acct_id,
            request.user.username,
        )

        return Response(
            {
                'status': 'success',
                'message': 'Broker account removed',
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None) -> Response:
        """
        Toggle broker account active status.

        POST /api/v1/broker-accounts/{id}/toggle_active/
        """
        account           = self.get_object()
        account.is_active = not account.is_active
        account.save()

        state = 'activated' if account.is_active else 'deactivated'

        logger.info(
            "Broker account %s: %s | user=%s",
            state,
            account.account_id,
            request.user.username,
        )

        return Response(
            {
                'status': 'success',
                'message': f'Broker account {state}',
                'data': BrokerAccountSerializer(account).data,
            }
        )

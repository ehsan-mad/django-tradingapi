from rest_framework import serializers
from django.utils import timezone
from .models import Order
from signals.serializers import TradingSignalSerializer


class OrderSerializer(serializers.ModelSerializer):
    """Read serializer - full order details"""
    signal = TradingSignalSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'signal',
            'broker_account',
            'order_id',
            'status',
            'executed_price',
            'executed_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating an order from a valid signal"""
    signal_id      = serializers.UUIDField(
                        write_only=True,
                        help_text="UUID of a valid trading signal"
                    )
    broker_account_id = serializers.UUIDField(
                        write_only=True,
                        help_text="UUID of your active broker account"
                    )

    class Meta:
        model  = Order
        fields = ['signal_id', 'broker_account_id']

    def validate_signal_id(self, value: str) -> str:
        """Signal must exist, belong to the user and be valid"""
        from signals.models import TradingSignal

        try:
            signal = TradingSignal.objects.get(
                id=value,
                user=self.context['request'].user,
            )
        except TradingSignal.DoesNotExist:
            raise serializers.ValidationError(
                "Signal not found or does not belong to you."
            )

        if not signal.is_valid:
            raise serializers.ValidationError(
                "Signal failed validation and cannot be used to create an order."
            )

        if hasattr(signal, 'order'):
            raise serializers.ValidationError(
                "An order already exists for this signal."
            )

        return value

    def validate_broker_account_id(self, value: str) -> str:
        """Broker account must exist, belong to the user and be active"""
        from brokers.models import BrokerAccount

        try:
            BrokerAccount.objects.get(
                id=value,
                user=self.context['request'].user,
                is_active=True,
            )
        except BrokerAccount.DoesNotExist:
            raise serializers.ValidationError(
                "Active broker account not found or does not belong to you."
            )

        return value

    def create(self, validated_data: dict) -> Order:
        from signals.models import TradingSignal
        from brokers.models import BrokerAccount
        import uuid

        signal         = TradingSignal.objects.get(id=validated_data['signal_id'])
        broker_account = BrokerAccount.objects.get(id=validated_data['broker_account_id'])

        return Order.objects.create(
            signal=signal,
            broker_account=broker_account,
            order_id=str(uuid.uuid4()),     # placeholder until broker assigns real ID
            status=Order.STATUS_PENDING,
        )


class OrderStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating order status"""
    status         = serializers.ChoiceField(
                        choices=Order.STATUS_CHOICES,
                        help_text="New status for the order"
                    )
    executed_price = serializers.DecimalField(
                        max_digits=12,
                        decimal_places=4,
                        required=False,
                        help_text="Required when status is 'executed'"
                    )

    def validate(self, data: dict) -> dict:
        if data['status'] == Order.STATUS_EXECUTED and not data.get('executed_price'):
            raise serializers.ValidationError(
                "executed_price is required when setting status to 'executed'."
            )
        return data
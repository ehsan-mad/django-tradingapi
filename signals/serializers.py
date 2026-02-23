from rest_framework import serializers
from decimal import Decimal
from .models import TradingSignal


class TradingSignalSerializer(serializers.ModelSerializer):
    """Read serializer - displays full signal details"""
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = TradingSignal
        fields = [
            'id',
            'user',
            'action',
            'instrument',
            'entry_price',
            'stop_loss',
            'take_profit',
            'raw_signal',
            'is_valid',
            'validation_errors',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class SignalWebhookSerializer(serializers.Serializer):
    """
    Validates incoming webhook payload.

    Expected signal format:
        BUY EURUSD @1.0860
        SL 1.0850
        TP 1.0890
    """
    signal = serializers.CharField(
        help_text="Signal text: BUY/SELL INSTRUMENT [@price]\nSL price\nTP price",
        style={'base_template': 'textarea.html'},
    )
    user_token = serializers.CharField(
        help_text="Your user ID",
        max_length=100,
    )

    def validate_signal(self, value: str) -> str:
        lines = [l.strip() for l in value.strip().split('\n') if l.strip()]
        if len(lines) < 3:
            raise serializers.ValidationError(
                "Signal must have at least 3 lines: action/instrument, SL, and TP"
            )
        return value
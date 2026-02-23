from rest_framework import serializers
from .models import BrokerAccount


class BrokerAccountSerializer(serializers.ModelSerializer):
    """Read serializer - full broker account details (no sensitive data)"""

    class Meta:
        model = BrokerAccount
        fields = [
            'id',
            'broker_name',
            'account_id',
            'account_name',
            'server',
            'is_active',
            'is_demo',
            'balance',
            'last_sync',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class BrokerAccountCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a broker account"""
    api_key = serializers.CharField(
        write_only=True,
        help_text="Your broker API key or password (stored encrypted)"
    )

    class Meta:
        model = BrokerAccount
        fields = [
            'broker_name',
            'account_name',
            'api_key',
            'server',
            'is_demo',
        ]

    def create(self, validated_data: dict) -> BrokerAccount:
        """Create broker account with auto-generated account_id and encrypted API key"""
        import uuid
        api_key = validated_data.pop('api_key')
        validated_data['user'] = self.context['request'].user
        validated_data['account_id'] = str(uuid.uuid4())  # auto-generate

        # Create instance without saving to DB yet
        account = BrokerAccount(**validated_data)

        # Encrypt and set the API key
        account.set_api_key(api_key)
        account.save()

        return account


class BrokerAccountUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating broker account fields"""
    api_key = serializers.CharField(
        write_only=True,
        required=False,
        help_text="Update your API key (leave blank to keep current)"
    )

    class Meta:
        model = BrokerAccount
        fields = [
            'account_name',
            'server',
            'is_active',
            'is_demo',
            'api_key',
        ]

    def update(self, instance: BrokerAccount, validated_data: dict) -> BrokerAccount:
        """Update broker account, re-encrypting API key if provided"""
        api_key = validated_data.pop('api_key', None)

        if api_key:
            instance.set_api_key(api_key)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

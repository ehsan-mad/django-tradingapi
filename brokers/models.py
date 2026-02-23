from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from cryptography.fernet import Fernet
from api.models import BaseModel


class BrokerAccount(BaseModel):
    """Model for storing user broker account credentials"""
    
    BROKER_CHOICES = [
        ('metatrader4', 'MetaTrader 4'),
        ('metatrader5', 'MetaTrader 5'),
        ('ctrader', 'cTrader'),
        ('mock', 'Mock Broker'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='broker_accounts'
    )
    broker_name = models.CharField(
        max_length=50,
        choices=BROKER_CHOICES,
        help_text="Broker platform name"
    )
    account_id = models.CharField(
        max_length=100,
        unique=True,
        editable=False,
        help_text="Auto-generated broker account ID"
    )
    account_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Display name for this account"
    )
    encrypted_api_key = models.BinaryField(
        help_text="Encrypted API key or password"
    )
    server = models.CharField(
        max_length=100,
        blank=True,
        help_text="Broker server (for MT4/MT5)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this account is active for trading"
    )
    is_demo = models.BooleanField(
        default=True,
        help_text="Whether this is a demo account"
    )
    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Account balance (updated periodically)"
    )
    last_sync = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time account was synchronized"
    )
    
    class Meta:
        db_table = 'broker_accounts'
        unique_together = [['user', 'broker_name', 'account_id']]
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['broker_name', 'is_active']),
        ]
    
    def set_api_key(self, api_key: str) -> None:
        """Encrypt and store API key"""
        fernet = Fernet(settings.BROKER_ENCRYPTION_KEY)
        self.encrypted_api_key = fernet.encrypt(api_key.encode())
    
    def get_api_key(self) -> str:
        """Decrypt and return API key"""
        fernet = Fernet(settings.BROKER_ENCRYPTION_KEY)
        return fernet.decrypt(self.encrypted_api_key).decode()
    
    def __str__(self) -> str:
        demo_label = " (Demo)" if self.is_demo else ""
        return f"{self.broker_name} - {self.account_id}{demo_label} ({self.user.username})"
    
    @property
    def display_name(self) -> str:
        """Return display name or generated name"""
        return self.account_name or f"{self.broker_name} {self.account_id}"
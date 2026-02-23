from django.db import models

# Create your models here.
from django.contrib.auth.models import User
from api.models import BaseModel


class TradingSignal(BaseModel):
    """Model for storing incoming trading signals from webhooks"""
    
    ACTION_CHOICES = [
        ('BUY', 'Buy'),
        ('SELL', 'Sell'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='trading_signals'
    )
    action = models.CharField(
        max_length=4, 
        choices=ACTION_CHOICES,
        help_text="Trading action: BUY or SELL"
    )
    instrument = models.CharField(
        max_length=20,
        help_text="Trading instrument e.g., EURUSD, GBPUSD"
    )
    entry_price = models.DecimalField(
        max_digits=12, 
        decimal_places=4, 
        null=True, 
        blank=True,
        help_text="Optional entry price from signal"
    )
    stop_loss = models.DecimalField(
        max_digits=12, 
        decimal_places=4,
        help_text="Stop loss price"
    )
    take_profit = models.DecimalField(
        max_digits=12, 
        decimal_places=4,
        help_text="Take profit price"
    )
    raw_signal = models.TextField(
        help_text="Original signal text received via webhook"
    )
    is_valid = models.BooleanField(
        default=False,
        help_text="Whether the signal passed validation"
    )
    validation_errors = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Validation error messages if signal is invalid"
    )
    
    class Meta:
        db_table = 'trading_signals'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['instrument', 'action']),
            models.Index(fields=['is_valid', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self) -> str:
        return f"{self.action} {self.instrument} - {self.user.username}"
    
    @property
    def has_entry_price(self) -> bool:
        """Check if signal has an entry price specified"""
        return self.entry_price is not None
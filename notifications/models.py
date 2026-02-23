from django.db import models
from django.contrib.auth.models import User
from api.models import BaseModel


class Notification(BaseModel):
    """Model for storing user notifications"""
    
    TYPE_CHOICES = [
        ('order_executed', 'Order Executed'),
        ('order_closed', 'Order Closed'),
        ('order_rejected', 'Order Rejected'),
        ('signal_received', 'Signal Received'),
        ('account_connected', 'Account Connected'),
        ('system_alert', 'System Alert'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES
    )
    title = models.CharField(
        max_length=200,
        help_text="Notification title"
    )
    message = models.TextField(
        help_text="Notification message content"
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    is_read = models.BooleanField(
        default=False,
        help_text="Whether user has read this notification"
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When notification was marked as read"
    )
    related_order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Related order if applicable"
    )
    data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional notification data"
    )
    
    class Meta:
        db_table = 'notifications'
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notification_type', 'created_at']),
            models.Index(fields=['priority', 'is_read']),
        ]
        ordering = ['-created_at']
    
    def mark_as_read(self) -> None:
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = models.functions.Now()
            self.save(update_fields=['is_read', 'read_at', 'updated_at'])
    
    def __str__(self) -> str:
        read_status = "✓" if self.is_read else "●"
        return f"{read_status} {self.title} ({self.user.username})"
from django.db import models
from django.utils import timezone
from api.models import BaseModel


class Order(BaseModel):
    """Model for storing processed orders from trading signals"""

    STATUS_PENDING   = 'pending'
    STATUS_EXECUTED  = 'executed'
    STATUS_CLOSED    = 'closed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_REJECTED  = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING,   'Pending'),
        (STATUS_EXECUTED,  'Executed'),
        (STATUS_CLOSED,    'Closed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_REJECTED,  'Rejected'),
    ]
    
    signal = models.OneToOneField(
        'signals.TradingSignal',
        on_delete=models.CASCADE,
        related_name='order'
    )
    broker_account = models.ForeignKey(
        'brokers.BrokerAccount',
        on_delete=models.CASCADE,
        related_name='orders'
    )
    order_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique order ID from broker or system generated"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    executed_price = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Actual execution price"
    )
    executed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When order was executed"
    )
    volume = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1,
        help_text="Order volume/lot size"
    )
    profit_loss = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Current or final P&L"
    )
    commission = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        help_text="Broker commission"
    )
    swap = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        help_text="Swap/rollover fees"
    )
    closed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When order was closed"
    )
    close_price = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Price at which order was closed"
    )
    rejection_reason = models.TextField(
        blank=True,
        help_text="Reason for rejection if status is rejected"
    )
    
    class Meta:
        db_table = 'orders'
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['broker_account', 'status']),
            models.Index(fields=['executed_at']),
            # Removed signal__user index - can't use relationship lookups in indexes
        ]
        ordering = ['-created_at']
    
    @property
    def user(self):
        """Get user from related signal"""
        return self.signal.user
    
    @property
    def instrument(self) -> str:
        """Get instrument from related signal"""
        return self.signal.instrument
    
    @property
    def action(self) -> str:
        """Get action from related signal"""
        return self.signal.action
    
    def mark_executed(self, price: float, executed_time: timezone.datetime = None) -> None:
        """Mark order as executed with price and time"""
        self.status = 'executed'
        self.executed_price = price
        self.executed_at = executed_time or timezone.now()
        self.save(update_fields=['status', 'executed_price', 'executed_at', 'updated_at'])
    
    def mark_closed(self, close_price: float, profit_loss: float = None) -> None:
        """Mark order as closed"""
        self.status = 'closed'
        self.close_price = close_price
        self.closed_at = timezone.now()
        if profit_loss is not None:
            self.profit_loss = profit_loss
        self.save(update_fields=['status', 'close_price', 'closed_at', 'profit_loss', 'updated_at'])
    
    def __str__(self) -> str:
        return f"Order {self.order_id} - {self.signal.action} {self.signal.instrument} ({self.status})"


class OrderHistory(BaseModel):
    """Model for tracking order status changes and updates"""
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='history'
    )
    previous_status = models.CharField(
        max_length=20,
        choices=Order.STATUS_CHOICES
    )
    new_status = models.CharField(
        max_length=20,
        choices=Order.STATUS_CHOICES
    )
    changed_by = models.CharField(
        max_length=100,
        default='system',
        help_text="What triggered the status change"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the change"
    )
    
    class Meta:
        db_table = 'order_history'
        ordering = ['-created_at']
    
    def __str__(self) -> str:
        return f"{self.order.order_id}: {self.previous_status} -> {self.new_status}"
import logging
from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework import status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TradingSignal
from .serializers import SignalWebhookSerializer, TradingSignalSerializer

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Signal Parsing Helpers
# ------------------------------------------------------------------

def parse_first_line(line: str) -> dict | None:
    """
    Parse the first line of the signal text.

    Valid formats:
        BUY EURUSD              (market order, no price)
        BUY EURUSD @1.0860      (limit order with price)
        SELL GBPUSD @1.2600

    Returns dict with action, instrument, entry_price or None if invalid.
    """
    parts = line.strip().upper().split()

    # Must have at least: ACTION INSTRUMENT
    if len(parts) < 2:
        logger.debug("First line too short: %s", parts)
        return None

    action = parts[0]           # e.g. BUY
    instrument = parts[1]       # e.g. EURUSD

    # Action must be BUY or SELL
    if action not in ('BUY', 'SELL'):
        logger.debug("Invalid action: %s", action)
        return None

    # Instrument must be exactly 6 alphabetic characters e.g. EURUSD
    if len(instrument) != 6 or not instrument.isalpha():
        logger.debug("Invalid instrument: %s", instrument)
        return None

    # Optional price: third part starts with @ e.g. @1.0860
    entry_price = None
    if len(parts) == 3:
        price_part = parts[2]
        if price_part.startswith('@'):
            try:
                entry_price = Decimal(price_part[1:])   # strip the @ then convert
            except Exception:
                logger.debug("Invalid entry price: %s", price_part)
                return None
        else:
            logger.debug("Third part does not start with @: %s", price_part)
            return None

    return {
        'action': action,
        'instrument': instrument,
        'entry_price': entry_price,
    }


def parse_price_line(line: str, prefix: str) -> Decimal | None:
    """
    Parse a price line like:
        SL 1.0850
        TP 1.0890

    prefix is either 'SL' or 'TP'.
    Returns the Decimal price or None if invalid.
    """
    parts = line.strip().upper().split()

    # Must have exactly: PREFIX VALUE  e.g. SL 1.0850
    if len(parts) != 2:
        logger.debug("Price line wrong format: %s", parts)
        return None

    if parts[0] != prefix:
        return None

    try:
        return Decimal(parts[1])
    except Exception:
        logger.debug("Invalid price value: %s", parts[1])
        return None


def parse_signal(text: str) -> dict | None:
    """
    Parse full signal text into a structured dict.

    Expected format:
        BUY EURUSD @1.0860      <- first line  (price optional)
        SL 1.0850               <- second line
        TP 1.0890               <- third line

    Returns dict with action, instrument, entry_price, stop_loss, take_profit
    or None if the text is invalid.
    """
    # Normalize literal \n from browser input and remove blank lines
    text = text.replace('\\n', '\n')
    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]

    logger.debug("Signal lines: %s", lines)

    if len(lines) < 3:
        logger.debug("Not enough lines: expected 3, got %d", len(lines))
        return None

    # Parse each line separately using focused helpers
    first = parse_first_line(lines[0])
    if not first:
        logger.debug("Failed to parse first line: %s", lines[0])
        return None

    stop_loss = None
    take_profit = None

    # SL and TP can appear in any order after the first line
    for line in lines[1:]:
        upper = line.strip().upper()

        if upper.startswith('SL'):
            stop_loss = parse_price_line(line, 'SL')

        elif upper.startswith('TP'):
            take_profit = parse_price_line(line, 'TP')

    if stop_loss is None:
        logger.debug("Missing SL")
        return None

    if take_profit is None:
        logger.debug("Missing TP")
        return None

    return {
        'action': first['action'],
        'instrument': first['instrument'],
        'entry_price': first['entry_price'],
        'stop_loss': stop_loss,
        'take_profit': take_profit,
    }


def validate_prices(parsed: dict) -> tuple[bool, dict]:
    """
    Validate SL/TP price logic for BUY and SELL orders.

    BUY rules:
        With entry : SL < entry < TP
        No entry   : SL < TP

    SELL rules:
        With entry : TP < entry < SL
        No entry   : TP < SL
    """
    errors = {}
    action = parsed['action']
    sl     = parsed['stop_loss']
    tp     = parsed['take_profit']
    entry  = parsed.get('entry_price')

    if action == 'BUY':
        if entry and not (sl < entry < tp):
            errors['price_logic'] = (
                f'BUY order requires SL < entry < TP. '
                f'Got SL={sl} entry={entry} TP={tp}'
            )
        elif not entry and not (sl < tp):
            errors['price_logic'] = (
                f'BUY order requires SL < TP. '
                f'Got SL={sl} TP={tp}'
            )

    elif action == 'SELL':
        if entry and not (tp < entry < sl):
            errors['price_logic'] = (
                f'SELL order requires TP < entry < SL. '
                f'Got TP={tp} entry={entry} SL={sl}'
            )
        elif not entry and not (tp < sl):
            errors['price_logic'] = (
                f'SELL order requires TP < SL. '
                f'Got TP={tp} SL={sl}'
            )

    return (len(errors) == 0, errors)


# ------------------------------------------------------------------
# Views
# ------------------------------------------------------------------

class TradingSignalViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve your trading signals.

    GET /api/v1/signals/       - list all signals
    GET /api/v1/signals/{id}/  - retrieve a single signal
    """
    serializer_class = TradingSignalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TradingSignal.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


class SignalWebhookView(APIView):
    """
    Receive a trading signal via webhook.

    POST /webhook/receive-signal/

    Fields:
        signal     - signal text (see format below)
        user_token - your user ID

    Signal format:
        BUY EURUSD @1.0860
        SL 1.0850
        TP 1.0890
    """
    permission_classes = [AllowAny]
    parser_classes = [FormParser, MultiPartParser]
    renderer_classes = [JSONRenderer, BrowsableAPIRenderer]
    serializer_class = SignalWebhookSerializer

    def get_serializer(self, *args, **kwargs) -> SignalWebhookSerializer:
        """Required for DRF browsable API to render form fields."""
        return SignalWebhookSerializer(*args, **kwargs)

    def get(self, request) -> Response:
        """Renders the DRF browsable form for browser testing."""
        return Response(
            {
                'status': 'info',
                'message': 'Send a POST request with signal and user_token',
                'example_payload': {
                    'signal': 'BUY EURUSD @1.0860\nSL 1.0850\nTP 1.0890',
                    'user_token': '1',
                },
                'signal_format': {
                    'line_1': 'BUY or SELL  INSTRUMENT  [@entry_price optional]',
                    'line_2': 'SL <stop_loss_price>',
                    'line_3': 'TP <take_profit_price>',
                },
            }
        )

    def post(self, request) -> Response:
        serializer = SignalWebhookSerializer(data=request.data)

        if not serializer.is_valid():
            logger.warning("Webhook validation errors: %s", serializer.errors)
            return Response(
                {
                    'status': 'error',
                    'errors': serializer.errors,
                    'message': 'Invalid payload',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        signal_text = serializer.validated_data['signal']
        user_token  = serializer.validated_data['user_token']

        # Resolve user from token
        user = self._get_user(user_token)
        if not user:
            return Response(
                {
                    'status': 'error',
                    'message': f'No user found with id: {user_token}',
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Parse signal text using simple helpers above
        parsed = parse_signal(signal_text)
        if not parsed:
            return Response(
                {
                    'status': 'error',
                    'message': (
                        'Could not parse signal text. '
                        'Expected: BUY/SELL INSTRUMENT [@price] '
                        'then SL and TP on separate lines.'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate price logic
        is_valid, validation_errors = validate_prices(parsed)

        # Persist signal
        signal = TradingSignal.objects.create(
            user=user,
            action=parsed['action'],
            instrument=parsed['instrument'],
            entry_price=parsed.get('entry_price'),
            stop_loss=parsed['stop_loss'],
            take_profit=parsed['take_profit'],
            raw_signal=signal_text,
            is_valid=is_valid,
            validation_errors=validation_errors,
        )

        logger.info(
            "Signal created: %s %s | user=%s | valid=%s",
            signal.action,
            signal.instrument,
            user.username,
            is_valid,
        )

        return Response(
            {
                'status': 'success',
                'message': 'Signal received and processed',
                'data': TradingSignalSerializer(signal).data,
            },
            status=status.HTTP_200_OK,
        )

    def _get_user(self, token: str) -> User | None:
        try:
            return User.objects.get(id=int(token))
        except (User.DoesNotExist, ValueError, TypeError):
            return None
"""Thin client for the Bila payments API.

Docs: https://docs.usebila.com  (collections + webhook signing)
Only the two calls this shop needs are implemented: initiate a mobile money
collection, and read a collection's status back by our own reference.
"""
import hashlib
import hmac
import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TIMEOUT = 20

# Zambian mobile money prefixes -> Bila `operator` enum.
# ponytail: prefix table, replace with Bila's operator-lookup endpoint if they add one.
OPERATOR_PREFIXES = {
    'mtn': ('96', '76'),
    'airtel': ('97', '77'),
    'zamtel': ('95', '75'),
}

# Bila collection statuses -> is this terminal, and did it succeed?
SUCCESS_STATUSES = {'successful'}
FAILURE_STATUSES = {'failed'}


class BilaError(Exception):
    """Any failure talking to Bila. The message is safe to log, not to display raw."""


def normalise_phone(raw):
    """Return a Zambian MSISDN as 260XXXXXXXXX, or raise ValueError."""
    digits = ''.join(ch for ch in raw if ch.isdigit())

    if digits.startswith('260'):
        national = digits[3:]
    elif digits.startswith('0'):
        national = digits[1:]
    elif len(digits) == 9:
        national = digits
    else:
        raise ValueError('Enter a Zambian mobile number, e.g. 0977123456.')

    if len(national) != 9:
        raise ValueError('Enter a Zambian mobile number, e.g. 0977123456.')

    return f'260{national}'


def detect_operator(phone):
    """Map a normalised 260XXXXXXXXX number to a Bila operator, or raise ValueError."""
    prefix = phone[3:5]
    for operator, prefixes in OPERATOR_PREFIXES.items():
        if prefix in prefixes:
            return operator
    raise ValueError('That number is not on MTN, Airtel or Zamtel mobile money.')


def _request(method, path, **kwargs):
    api_key = settings.BILA_API_KEY
    if not api_key:
        raise BilaError('BILA_API_KEY is not configured.')

    url = f'{settings.BILA_BASE_URL.rstrip("/")}/api/v1/bila{path}'
    try:
        response = requests.request(
            method, url, timeout=TIMEOUT,
            headers={'x-api-key': api_key, 'Content-Type': 'application/json'},
            **kwargs,
        )
    except requests.RequestException as exc:
        raise BilaError(f'Could not reach Bila: {exc}') from exc

    try:
        payload = response.json()
    except ValueError:
        raise BilaError(f'Bila returned a non-JSON {response.status_code} response.')

    if not response.ok:
        message = payload.get('message') or f'HTTP {response.status_code}'
        raise BilaError(f'Bila rejected the request: {message}')

    return payload.get('data') or {}


def initiate_collection(*, amount, reference, phone, operator, narration, customer_name):
    """Push a mobile money prompt to the customer's handset."""
    body = {
        'amount': float(amount),
        'reference': reference,
        'phone': phone,
        'operator': operator,
        'country': settings.BILA_COUNTRY,
        'walletId': settings.BILA_WALLET_ID,
        'bearer': settings.BILA_FEE_BEARER,
        'narration': narration[:100],
        'customerName': customer_name[:100],
    }
    logger.info('Bila collection request %s for %s %s', reference, amount, operator)
    return _request('POST', '/collections/mobile-money', json=body)


def get_collection(reference):
    """Authoritative status for one of our references."""
    return _request('GET', f'/collections/status/{reference}')


def verify_webhook(raw_body, timestamp_header, signature_header, max_age_seconds=300):
    """HMAC-SHA256 over `{timestamp}.{rawBody}`, per Bila's webhook docs."""
    secret = settings.BILA_WEBHOOK_SECRET
    if not secret or not timestamp_header or not signature_header:
        return False

    try:
        timestamp = int(timestamp_header)
    except (TypeError, ValueError):
        return False

    if abs(int(time.time()) - timestamp) > max_age_seconds:
        return False

    digest = hmac.new(
        secret.encode(), f'{timestamp}.'.encode() + raw_body, hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(f'sha256={digest}', signature_header)

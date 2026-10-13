"""Strict transport validation shared by services and HTTP actions."""
import re
from rest_framework.exceptions import ValidationError


def whole_units(value, *, minimum=0, maximum=2147483647):
    # int(1.9) and int(True) silently accept values the inventory cannot represent.
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValidationError('Quantity must be a whole number.')
    if isinstance(value, str) and not re.fullmatch(r'[0-9]+', value):
        raise ValidationError('Quantity must be a whole number.')
    number = int(value)
    if not minimum <= number <= maximum:
        raise ValidationError(f'Quantity must be between {minimum} and {maximum}.')
    return number

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from rest_framework.exceptions import ValidationError

def money(value, exponent=2):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0 or amount > Decimal('999999999999'):
            raise ValueError()
        return amount.quantize(Decimal(10) ** -exponent, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError('Invalid nonnegative monetary amount.')

def allocate(total, weights, exponent=2):
    """Largest-remainder allocation with stable input-order tie breaking."""
    scale = 10 ** exponent
    cents = int(money(total, exponent) * scale)
    total_weight = sum(Decimal(str(w)) for w in weights)
    if not total_weight:
        return [Decimal(0) for _ in weights]
    raw = [Decimal(cents) * Decimal(str(w)) / total_weight for w in weights]
    values = [int(x) for x in raw]
    for i in sorted(range(len(raw)), key=lambda i: (-(raw[i] - values[i]), i))[:cents - sum(values)]:
        values[i] += 1
    return [Decimal(v) / scale for v in values]


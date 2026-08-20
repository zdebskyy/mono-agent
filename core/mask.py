import re

MONEY_KEYS = {"balance_minor", "amount_minor", "cashback_minor", "goal_minor"}
ID_KEYS = {"id", "account", "masked_pan", "clientId", "iban"}

MONEY_TEXT = re.compile(
    r"(-?\d[\d\s ]*(?:[.,]\d+)?)(\s*)(₴|грн\.?|гривень|гривні|UAH|USD|EUR|PLN|\$|€)",
    re.IGNORECASE)


def _digits(value):
    return re.sub(r"\d", "#", str(value))


def ident(value):
    text = str(value)
    return text if len(text) <= 6 else f"{text[:4]}…"


def obj(value):
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key in MONEY_KEYS and isinstance(item, (int, float)):
                out[key] = _digits(item)
            elif key in ID_KEYS and item is not None:
                out[key] = ident(item)
            else:
                out[key] = obj(item)
        return out
    if isinstance(value, list):
        return [obj(item) for item in value]
    return value


CARD_TEXT = re.compile(r"\*\s?\d{4}")


def text(value):
    value = MONEY_TEXT.sub(lambda m: _digits(m.group(1)) + m.group(2) + m.group(3), value)
    return CARD_TEXT.sub(lambda m: _digits(m.group(0)), value)

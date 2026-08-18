from datetime import datetime

from config import TOOLS_VARIANT, KYIV
from domain import mono

MAX_ITEMS = 150


def _as_ts(value, field):
    try:
        ts = int(value)
    except (TypeError, ValueError):
        return None, mono.fail("bad_timestamp",
                               f"{field}={value!r} не є Unix-часом у секундах",
                               hint="Передати ціле число секунд, напр. 1787062841")
    if ts > 10_000_000_000:
        return None, mono.fail("bad_timestamp",
                               f"{field}={ts} схоже на мілісекунди",
                               hint="monobank приймає Unix-час у секундах (10 цифр)")
    return ts, None


def list_accounts():
    resp = mono.client_info()
    if "error" in resp:
        return resp

    data = resp["data"]
    accounts = [{"id": a.get("id"),
                 "type": a.get("type"),
                 "currency": mono.CURRENCIES.get(a.get("currencyCode"), a.get("currencyCode")),
                 "balance_minor": a.get("balance"),
                 "masked_pan": (a.get("maskedPan") or [None])[0]}
                for a in data.get("accounts", [])]
    jars = [{"id": j.get("id"),
             "title": j.get("title"),
             "currency": mono.CURRENCIES.get(j.get("currencyCode"), j.get("currencyCode")),
             "balance_minor": j.get("balance"),
             "goal_minor": j.get("goal")}
            for j in data.get("jars", [])]

    return {"accounts": accounts, "jars": jars,
            "note": "balance_minor — у копійках/центах, ділити на 100"}


def get_statement(account, from_ts, to_ts):
    from_ts, err = _as_ts(from_ts, "from_ts")
    if err:
        return err
    to_ts, err = _as_ts(to_ts, "to_ts")
    if err:
        return err

    resp = mono.statement(account, from_ts, to_ts)
    if "error" in resp:
        return resp

    raw = resp["data"]
    total = len(raw)
    if total == 0:
        return {"account": account, "count": 0, "transactions": [],
                "note": "За вказаний період операцій немає."}

    items = []
    for t in raw[:MAX_ITEMS]:
        item = {"time": datetime.fromtimestamp(t["time"], KYIV).strftime("%Y-%m-%d %H:%M"),
                "description": t.get("description"),
                "amount_minor": t.get("amount"),
                "mcc": t.get("mcc")}
        if t.get("cashbackAmount"):
            item["cashback_minor"] = t["cashbackAmount"]
        if t.get("comment"):
            item["comment"] = t["comment"]
        if t.get("hold"):
            item["hold"] = True
        items.append(item)

    out = {"account": account, "count": len(items), "transactions": items,
           "note": "amount_minor — у копійках, відʼємне значення = витрата"}
    if total > MAX_ITEMS:
        out["truncated"] = True
        out["total_available"] = total
        out["warning"] = f"Показано {MAX_ITEMS} операцій з {total}. Підсумок за період буде неповним."
    return out


IMPL = {"list_accounts": list_accounts, "get_statement": get_statement}


def dispatch(name, args):
    fn = IMPL.get(name)
    if not fn:
        return {"error": "unknown_tool", "message": name}
    try:
        return fn(**args)
    except TypeError as e:
        return {"error": "bad_args", "message": str(e)}


V1 = [
    {"name": "list_accounts",
     "description": "Повертає інформацію про клієнта та перелік його рахунків і банок.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "get_statement",
     "description": "Отримання виписки за період.",
     "input_schema": {"type": "object", "properties": {
         "account": {"type": "string",
                     "description": "Ідентифікатор рахунку або банки з переліку, або 0 — дефолтний рахунок."},
         "from_ts": {"type": "integer", "description": "Початок часу виписки."},
         "to_ts": {"type": "integer", "description": "Останній час виписки."}},
         "required": ["account", "from_ts", "to_ts"]}},
]

V2 = [
    {"name": "list_accounts",
     "description": "Крок 1 з 2 для будь-якого запиту про витрати, надходження або баланс. "
                    "Повертає рахунки та банки клієнта разом з їхніми id, валютою і балансом. "
                    "id рахунку неможливо дізнатись жодним іншим способом.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "get_statement",
     "description": "Крок 2 з 2. Виписка по ОДНОМУ рахунку за період. "
                    "Викликати лише після list_accounts, взявши id звідти.",
     "input_schema": {"type": "object", "properties": {
         "account": {"type": "string",
                     "description": "id рахунку або банки, скопійований з відповіді list_accounts. "
                                    "Не назва картки, не валюта, не номер картки. "
                                    "Значення \"0\" (дефолтний рахунок) НЕ використовувати: "
                                    "у клієнта кілька рахунків у різних валютах, і дефолтний "
                                    "майже ніколи не є тим, про який питає користувач."},
         "from_ts": {"type": "integer",
                     "description": "Початок періоду. Unix-час у СЕКУНДАХ (10 цифр), "
                                    "не мілісекунди і не рядок з датою."},
         "to_ts": {"type": "integer",
                   "description": "Кінець періоду, Unix-час у секундах. Максимальне вікно — "
                                  "2682000 с (31 доба). Довший період розбивати на кілька викликів."}},
         "required": ["account", "from_ts", "to_ts"]}},
]

VARIANTS = {"v1": V1, "v2": V2}


def tools(variant=None):
    return VARIANTS[variant or TOOLS_VARIANT]

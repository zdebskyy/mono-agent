import httpx

from config import MONO_TOKEN, HTTP_TIMEOUT

BASE_URL = "https://api.monobank.ua"
MAX_WINDOW_SEC = 2682000

CURRENCIES = {980: "UAH", 840: "USD", 978: "EUR", 826: "GBP", 985: "PLN"}

HTTP_ERRORS = {401: "unauthorized", 403: "forbidden", 404: "not_found", 429: "rate_limited"}

HINTS = {
    "no_token": "MONO_TOKEN не заданий у .env — отримати на https://api.monobank.ua/",
    "unauthorized": "Токен недійсний або прострочений.",
    "forbidden": "Токен не дає доступу до цих даних.",
    "rate_limited": "monobank приймає не частіше ніж 1 запит на 60 секунд до цієї функції.",
    "timeout": "Мережа або monobank не відповіли вчасно.",
}


def fail(code, message, **extra):
    out = {"error": code, "message": message}
    if code in HINTS:
        out["hint"] = HINTS[code]
    out.update(extra)
    return out


def _describe(resp):
    try:
        body = resp.json()
    except ValueError:
        return resp.text[:200].strip() or f"HTTP {resp.status_code}"
    if isinstance(body, dict) and "errorDescription" in body:
        return body["errorDescription"]
    return str(body)[:200]


def _get(path):
    if not MONO_TOKEN:
        return fail("no_token", "Токен monobank не налаштований")
    try:
        resp = httpx.get(f"{BASE_URL}{path}",
                         headers={"X-Token": MONO_TOKEN},
                         timeout=HTTP_TIMEOUT)
    except httpx.TimeoutException:
        return fail("timeout", f"monobank не відповів за {HTTP_TIMEOUT} с")
    except httpx.RequestError as e:
        return fail("network", f"{type(e).__name__}: {e}")

    if resp.status_code == 200:
        return {"data": resp.json()}

    code = HTTP_ERRORS.get(resp.status_code, f"http_{resp.status_code}")
    return fail(code, _describe(resp), http_status=resp.status_code)


def client_info():
    return _get("/personal/client-info")


def statement(account, from_ts, to_ts):
    if from_ts > to_ts:
        return fail("bad_range", f"Початок періоду ({from_ts}) пізніший за кінець ({to_ts})")
    window = to_ts - from_ts
    if window > MAX_WINDOW_SEC:
        return fail("window_too_large",
                    f"Період {window} с перевищує ліміт monobank {MAX_WINDOW_SEC} с (31 доба + 1 год)",
                    hint="Розбити період на кілька викликів по 31 добі або менше")
    return _get(f"/personal/statement/{account}/{from_ts}/{to_ts}")

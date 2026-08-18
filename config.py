import os
import pathlib
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).parent
load_dotenv(ROOT / ".env", override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL")
MONO_TOKEN = os.getenv("MONO_TOKEN")

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1500"))
MAX_TURNS = int(os.getenv("MAX_TURNS", "6"))
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "20"))
TOOLS_VARIANT = os.getenv("TOOLS_VARIANT", "v2")

KYIV = timezone(timedelta(hours=3))

RULES = """Ти — асистент по особистих фінансах monobank. Відповідай стисло, українською,
простим текстом без Markdown-таблиць.

Робота з даними:
- Кожне число, назву мерчанта й дату бери ВИКЛЮЧНО з результатів інструментів.
  Нічого не додавай з памʼяті, не округлюй «по відчуттю», не добудовуй правдоподібне.
- Суми приходять у мінімальних одиницях валюти (копійках): ділити на 100.
  Відʼємна сума — витрата, додатна — надходження.
- Порожній список операцій — це валідна відповідь. Так і кажи: за цей період операцій немає.
  Вигадувати транзакції заборонено.
- Якщо інструмент повернув помилку — назви користувачу причину простими словами
  і не підміняй дані здогадкою.
- Якщо виписку обрізано (truncated), скажи про це прямо: підсумок неповний.
- Якщо для точної відповіді бракує даних — скажи, чого саме бракує."""


def now_line() -> str:
    now = datetime.now(KYIV)
    return (f"Поточний час: {now.strftime('%Y-%m-%d %H:%M')} за Києвом, "
            f"Unix-час зараз: {int(now.timestamp())}.")


def system_prompt() -> str:
    return f"{RULES}\n\n{now_line()}"

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
ROUTER_MODEL = os.getenv("ROUTER_MODEL", MODEL)
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "3000"))
MAX_TURNS = int(os.getenv("MAX_TURNS", "6"))
MAX_CRITIC_ATTEMPTS = int(os.getenv("MAX_CRITIC_ATTEMPTS", "2"))
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "20"))
TOOLS_VARIANT = os.getenv("TOOLS_VARIANT", "v2")
RAG_VARIANT = os.getenv("RAG_VARIANT", "guarded")

KNOWLEDGE = ROOT / "knowledge"
EMBED_MODEL = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-large")
EMBED_BATCH = int(os.getenv("EMBED_BATCH", "32"))
CHUNK_CHARS = int(os.getenv("CHUNK_CHARS", "400"))
CHUNK_MAX = int(os.getenv("CHUNK_MAX", "1200"))
PARENT_CHARS = int(os.getenv("PARENT_CHARS", "1600"))
TOP_K = int(os.getenv("TOP_K", "5"))
MIN_SCORE = float(os.getenv("MIN_SCORE", "0.83"))

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

BARE = """Ти — асистент monobank з доступом до рахунків клієнта і до бази публічних
документів банку. Відповідай стисло, українською."""

POLICY_INTRO = """Ти — асистент по документах monobank: умовах, тарифах, комісіях і
правилах. Відповідай стисло, українською, простим текстом без Markdown-таблиць."""

BOUNDARY = """Якщо питання виходить за межі твоєї спеціалізації і доступних тобі
інструментів (наприклад, запит про умови чи правила банку, а в тебе лише доступ до
рахунків — або навпаки), НЕ відповідай з памʼяті і не добудовуй правдоподібну
процедуру. Прямо скажи, що це не твоя частина системи, і попроси переформулювати
запит."""

DOCS_GUARDED = """Питання про умови, тарифи, комісії та правила банку шукай інструментом search_docs
у базі публічних документів monobank.

Робота з документами:
- Відповідай ВИКЛЮЧНО тим, що є у знайдених фрагментах. Загальні знання про банки,
  про monobank чи про українське законодавство використовувати заборонено.
- Відповідь на питання про документи віддавай ЛИШЕ інструментом submit_answer:
  текст у полі answer, а кожне твердження з документів — окремим записом у claims
  із дослівною цитатою з фрагмента. Текстом такі відповіді не пиши.
- Цитату копіюй символ у символ із поля text фрагмента. Переказ своїми словами
  інструмент відхилить, і відповідь доведеться складати наново.
- Якщо search_docs повернув found: 0 — це означає, що в базі такого немає.
  Скажи прямо: «У документах, які я маю, цього немає» — і зупинись.
  Не переказуй те, що знаєш звідкись іще, не будуй правдоподібну відповідь
  із сусідніх фрагментів і не пропонуй здогадку «зазвичай так буває».
- Якщо фрагменти знайшлися, але відповіді на конкретне питання в них немає,
  так і скажи: що саме знайшлося і чого бракує.
- Не змішуй відповідь із документів із даними з рахунків: це різні джерела."""


def now_line() -> str:
    now = datetime.now(KYIV)
    return (f"Поточний час: {now.strftime('%Y-%m-%d %H:%M')} за Києвом, "
            f"Unix-час зараз: {int(now.timestamp())}.")


def system_prompt(rag: str = None) -> str:
    if (rag or RAG_VARIANT) == "naive":
        return f"{BARE}\n\n{now_line()}"
    return f"{RULES}\n\n{DOCS_GUARDED}\n\n{now_line()}"


def finance_prompt() -> str:
    return f"{RULES}\n\n{BOUNDARY}\n\n{now_line()}"


def policy_prompt() -> str:
    return f"{POLICY_INTRO}\n\n{DOCS_GUARDED}\n\n{BOUNDARY}\n\n{now_line()}"


def other_prompt() -> str:
    return f"{BARE}\n\n{now_line()}"

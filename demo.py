import sys

import config
from core import report
from core.agent import run_agent
from domain import kb, mono
from domain.tools import tools

HIDDEN = "--mask" in sys.argv


def play(query, variant="v2", max_turns=None, rag=None):
    max_turns = max_turns or config.MAX_TURNS
    rag = rag or config.RAG_VARIANT
    config.RAG_VARIANT = rag
    report.header(query, config.MODEL, variant, max_turns, rag)
    result = run_agent(query, tools(variant), system=config.system_prompt(rag),
                       max_turns=max_turns, on_step=report.stepper(HIDDEN))
    report.summary(result, HIDDEN)
    return result


def scene_1():
    print("── 1. Щасливий ланцюжок ─────────────────────────────────────")
    print("   list_accounts → id рахунку → get_statement. Другий виклик")
    print("   неможливий без результату першого.\n")
    play("Скільки я витратив за минулий тиждень?")


def scene_2():
    print("── 2. tool_error: токен monobank протух ─────────────────────")
    print("   Найчастіший збій у продакшені: банк відповідає, але не")
    print("   впізнає токен. Жоден інструмент не спрацював, тому агент")
    print("   не має чим відповідати — і мусить сказати саме це.\n")
    saved = mono.MONO_TOKEN
    mono.MONO_TOKEN = "expired-token"
    try:
        play("Скільки я витратив за минулий тиждень?")
    finally:
        mono.MONO_TOKEN = saved


def scene_3():
    print("── 3. turns_exhausted: ліміт кроків ─────────────────────────")
    print("   Виписка обмежена 31 добою, тож літо — це три виклики плюс")
    print("   список рахунків. При ліміті 3 агент не встигає і мусить")
    print("   сказати, чого саме не дістав.\n")
    play("Скільки я витратив за все літо?", max_turns=3)


def scene_4():
    print("── 4. api_error: модель недоступна ──────────────────────────")
    print("   Ключ зіпсовано навмисно. Збій провайдера — це стан,")
    print("   а не виняток, що вбиває процес.\n")
    saved = config.ANTHROPIC_API_KEY
    config.ANTHROPIC_API_KEY = "sk-broken-key-for-demo"
    try:
        play("Скільки я витратив учора?")
    finally:
        config.ANTHROPIC_API_KEY = saved


def scene_5():
    print("── 5. no_tool_used: питання не про дані ─────────────────────")
    print("   Питання про самого агента, а не про гроші. Інструменти не")
    print("   потрібні, і прогін позначається окремим станом: ця відповідь")
    print("   не спирається на виписку.\n")
    play("Привіт! Розкажи, що ти вмієш і як тобою користуватись.")


def scene_6():
    print("── 6. Челендж: опис проти опису ─────────────────────────────")
    print("   Той самий запит на двох варіантах описів get_statement.")
    print("   v1 дозволяє account=\"0\" (дефолтний рахунок), v2 вимагає id")
    print("   з list_accounts. Код інструментів однаковий.\n")
    print("v1 — опис з офіційної доки:")
    play("Скільки я витратив у доларах за минулий тиждень?", variant="v1")
    print("v2 — опис, що вимагає id з list_accounts:")
    play("Скільки я витратив у доларах за минулий тиждень?", variant="v2")


def scene_7():
    print("── 7. Порожній період: нічого не вигадувати ─────────────────")
    print("   Вузьке нічне вікно, де операцій немає. Інструмент повертає")
    print("   count: 0 — не помилку. Агент має сказати «операцій немає»,")
    print("   а не показати найближчі або правдоподібні.\n")
    play("Що я купував сьогодні між 3 і 4 ранку?")


def scene_8():
    print("── 8. База документів: питання іншими словами ───────────────")
    print("   Питання поставлене живою мовою, у документі — канцелярит.")
    print("   Пошук по змісту зводить їх разом, агент відповідає з")
    print("   посиланням на пункт документа.\n")
    play("Я загубив картку, що робити?")


def scene_9():
    print("── 9. Ембединги проти пошуку по словах ──────────────────────")
    print("   Без моделі: той самий запит двома способами по одному й")
    print("   тому ж індексу. BM25 шукає збіг слів, ембединги — збіг")
    print("   змісту.\n")
    for query in COMPARE:
        print(f"Запит: «{query}»")
        for label, hits in (("по словах", kb.keyword(query, 3)),
                            ("по змісту", kb.semantic(query, 3))):
            for i, hit in enumerate(hits, 1):
                clause = f" п. {hit['clause']}" if hit["clause"] else ""
                head = label if i == 1 else " " * len(label)
                print(f"  {head} {i}. [{hit['score']:8.4f}] {hit['title']}{clause}")
                print(f"              {' '.join(hit['text'].split())[:140]}")
        print()


def scene_10():
    print("── 10. Челендж Б: питання не з бази ─────────────────────────")
    print("   Питання звучить банківсько, але відповіді на нього в")
    print("   документах немає. naive віддає моделі 5 найближчих")
    print("   фрагментів попри слабку схожість; guarded відрізає їх")
    print("   порогом і повертає found: 0.\n")
    print("naive — без порога схожості:")
    play(OFF_TOPIC, rag="naive")
    print("guarded — поріг схожості плюс заборона відповідати з памʼяті:")
    play(OFF_TOPIC, rag="guarded")


COMPARE = ["Я загубив картку, що робити?",
           "Магазин списав більше, ніж я купив — як оскаржити?"]

OFF_TOPIC = "Які документи потрібні, щоб оформити військову пенсію?"

SCENES = {1: scene_1, 2: scene_2, 3: scene_3, 4: scene_4, 5: scene_5,
          6: scene_6, 7: scene_7, 8: scene_8, 9: scene_9, 10: scene_10}

if __name__ == "__main__":
    wanted = [int(a) for a in sys.argv[1:] if a.isdigit()] or sorted(SCENES)
    for number in wanted:
        SCENES[number]()

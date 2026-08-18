import sys

import config
from core import report
from core.agent import run_agent
from domain import mono
from domain.tools import tools

HIDDEN = "--mask" in sys.argv


def play(query, variant="v2", max_turns=None):
    max_turns = max_turns or config.MAX_TURNS
    report.header(query, config.MODEL, variant, max_turns)
    result = run_agent(query, tools(variant), max_turns=max_turns,
                       on_step=report.stepper(HIDDEN))
    report.summary(result, HIDDEN)
    return result


def scene_1():
    print("── 1. Щасливий ланцюжок ─────────────────────────────────────")
    print("   list_accounts → id рахунку → get_statement. Другий виклик")
    print("   неможливий без результату першого.\n")
    play("Скільки я витратив учора?")


def scene_2():
    print("── 2. tool_error: ліміт monobank ────────────────────────────")
    print("   monobank приймає 1 запит на 60 секунд. Одразу після сцени 1")
    print("   інструменти віддають 429 — агент має сказати це чесно,")
    print("   а не показати старі або вигадані числа.\n")
    play("А позавчора скільки вийшло?")


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
    print("   Порада не потребує банку. Агент відповідає без інструментів,")
    print("   і прогін позначається окремим станом: ця відповідь")
    print("   не спирається на виписку.\n")
    play("Порадь, як узагалі менше витрачати на каву?")


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


SCENES = {1: scene_1, 2: scene_2, 3: scene_3, 4: scene_4, 5: scene_5,
          6: scene_6, 7: scene_7}

if __name__ == "__main__":
    wanted = [int(a) for a in sys.argv[1:] if a.isdigit()] or sorted(SCENES)
    for number in wanted:
        SCENES[number]()

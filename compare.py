import config
from core.agent import run_agent
from core.router import run as run_router
from domain.tools import tools

QUERIES = [
    "Скільки я витратив за минулий тиждень?",
    "Я загубив картку, що робити?",
    "Привіт! Розкажи, що ти вмієш і як тобою користуватись.",
    "Магазин списав більше, ніж я купив — як оскаржити?",
    "Що я купував сьогодні між 3 і 4 ранку?",
]


def _line(label, result):
    usage = result["usage"]
    ok = result.get("checks", {}).get("ok") if result.get("checks") else None
    ok_mark = "" if ok is None else (" · перевірка OK" if ok else " · Є НЕПІДТВЕРДЖЕНЕ")
    print(f"  {label:<18} {result['outcome']:16} токени {usage['in']:>5}→{usage['out']:<4} "
          f"· {result['elapsed_sec']:>5.1f} с{ok_mark}")


def main():
    rows = []
    for query in QUERIES:
        print(f"\n«{query}»")
        baseline = run_agent(query, tools(), system=config.system_prompt())
        routed = run_router(query)
        _line("single agent", baseline)
        _line(f"router→{routed['route']}", routed)
        rows.append((baseline, routed))

    b_total = sum(r["usage"]["in"] + r["usage"]["out"] for r, _ in rows)
    r_total = sum(r["usage"]["in"] + r["usage"]["out"] for _, r in rows)
    delta = r_total - b_total
    print(f"\nРазом на {len(QUERIES)} запитах: single agent {b_total} токенів, "
          f"router {r_total} токенів ({delta:+d}, {delta / b_total * 100:+.1f}%)")


if __name__ == "__main__":
    main()

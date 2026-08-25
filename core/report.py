import json

from core import mask


def preview(output):
    if "error" in output:
        return f"{output['error']}: {output.get('message', '')}"
    if "accounts" in output:
        return f"{len(output['accounts'])} рахунків, {len(output['jars'])} банок"
    if "rejected" in output:
        return (f"unverified_claims: {output['message']} — "
                + "; ".join(f"#{r['claim']} {r['problem']}" for r in output["rejected"]))
    if output.get("delivered"):
        return f"відповідь прийнято, підтверджених цитат: {output['verified_claims']}"
    if "fragments" in output:
        if not output["found"]:
            return (f"0 фрагментів (найкраща схожість {output.get('best_score')} < "
                    f"поріг {output.get('threshold')})")
        top = output["fragments"][0]
        clause = f" п. {top['clause']}" if top.get("clause") else ""
        return (f"{output['found']} фрагментів · найкращий {top['score']}: "
                f"{top['doc']}{clause}")
    if "transactions" in output:
        return f"{output['count']} операцій" + (" (обрізано)" if output.get("truncated") else "")
    return json.dumps(output, ensure_ascii=False)[:120]


def stepper(hidden=False, verbose=False):
    counter = {"n": 0}
    hide = mask.obj if hidden else (lambda value: value)

    def on_step(step):
        counter["n"] += 1
        mark = "✗" if step["failed"] else "→"
        print(f"  [{counter['n']}] {step['tool']} "
              f"{json.dumps(hide(step['input']), ensure_ascii=False)}")
        print(f"      {mark} {preview(step['output'])}")
        if verbose:
            print(f"        {json.dumps(hide(step['output']), ensure_ascii=False)}")

    return on_step


def header(query, model, variant, max_turns, rag=None):
    print(f"\nЗапит: «{query}»")
    line = f"Модель: {model} · інструменти: {variant}"
    if rag:
        line += f" · база знань: {rag}"
    print(f"{line} · ліміт кроків: {max_turns}\n")


def checks(data):
    if not data:
        return
    if not data["grounded"]:
        print(f"Звірка з фрагментами: {data['note']}")
        return
    if data.get("mode") == "claims":
        line = f"Звірка цитат: {data['claims']} підтверджено видачею"
        if data["bounced"]:
            print(f"{line} · відповідь відхилялась {data['bounced']} раз(и)")
        else:
            print(line)
        return
    line = f"Звірка з фрагментами: посилань {data['citations']}"
    if isinstance(data.get("figures"), int):
        line += f", чисел {data['figures']}"
    print(f"{line} · {'усе підтверджено' if data['ok'] else 'Є НЕПІДТВЕРДЖЕНЕ'}")
    if data["unknown_citations"]:
        print(f"  ✗ немає у виданих фрагментах: п. {', п. '.join(data['unknown_citations'])}")
    if data.get("unknown_figures"):
        print(f"  ✗ числа, яких немає у виданих фрагментах: {', '.join(data['unknown_figures'])}")
    if isinstance(data.get("figures"), str):
        print(f"  · числа не звірялись — {data['figures'].split(': ')[1]}")


def summary(result, hidden=False):
    if not result["trace"]:
        print("  інструменти не викликались")
    usage = result["usage"]
    print(f"\nСтан: {result['outcome']} · кроків: {result['turns']} · "
          f"{result['elapsed_sec']} с · токени {usage['in']}→{usage['out']}")
    if result.get("error"):
        print(f"Помилка: {result['error']}")
    if result["failures"]:
        print(f"Збої інструментів: {[f['error'] for f in result['failures']]}")
    checks(result.get("checks"))
    answer = mask.text(result["answer"]) if hidden else result["answer"]
    print(f"\n{answer}\n")

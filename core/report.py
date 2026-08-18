import json

from core import mask


def preview(output):
    if "error" in output:
        return f"{output['error']}: {output.get('message', '')}"
    if "accounts" in output:
        return f"{len(output['accounts'])} рахунків, {len(output['jars'])} банок"
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


def header(query, model, variant, max_turns):
    print(f"\nЗапит: «{query}»")
    print(f"Модель: {model} · інструменти: {variant} · ліміт кроків: {max_turns}\n")


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
    answer = mask.text(result["answer"]) if hidden else result["answer"]
    print(f"\n{answer}\n")

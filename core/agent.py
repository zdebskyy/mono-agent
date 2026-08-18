import json
import time

from anthropic import Anthropic

import config
from domain.tools import dispatch, reset_session

OUTCOMES = ("ok", "tool_error", "turns_exhausted", "api_error", "no_tool_used")

EXHAUSTED_NUDGE = ("Ліміт кроків вичерпано. Більше інструментів не викликай. "
                   "Підсумуй те, що вже вдалося дізнатись, і прямо скажи користувачу, "
                   "яка частина відповіді лишилась недоступною і чому.")

EXHAUSTED_FALLBACK = ("Не вклався у відведену кількість кроків і не встиг зібрати дані. "
                      "Звузьте період або спитайте про один рахунок.")


def _client():
    if config.ANTHROPIC_BASE_URL:
        return Anthropic(api_key=config.ANTHROPIC_API_KEY,
                         base_url=config.ANTHROPIC_BASE_URL)
    return Anthropic(api_key=config.ANTHROPIC_API_KEY)


def _text(resp):
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def run_agent(query, tools, system=None, max_turns=None, on_step=None):
    system = system or config.system_prompt()
    max_turns = max_turns or config.MAX_TURNS
    client = None

    reset_session()

    messages = [{"role": "user", "content": query}]
    trace, failures = [], []
    started = time.time()
    usage = {"in": 0, "out": 0, "calls": 0}

    def finish(answer, outcome, **extra):
        return {"answer": answer, "outcome": outcome, "trace": trace,
                "failures": failures, "turns": len(trace),
                "elapsed_sec": round(time.time() - started, 2),
                "usage": usage, "query": query, **extra}

    def call(**kwargs):
        nonlocal client
        if client is None:
            client = _client()
        resp = client.messages.create(**kwargs)
        usage["calls"] += 1
        usage["in"] += resp.usage.input_tokens
        usage["out"] += resp.usage.output_tokens
        return resp

    for turn in range(max_turns):
        try:
            resp = call(model=config.MODEL, max_tokens=config.MAX_TOKENS,
                        system=system, messages=messages, tools=tools)
        except Exception as e:
            return finish("Сервіс моделі недоступний, відповісти зараз не можу.",
                          "api_error", error=f"{type(e).__name__}: {e}")

        if resp.stop_reason != "tool_use":
            answer = _text(resp)
            if not trace:
                return finish(answer, "no_tool_used")
            if all(step["failed"] for step in trace):
                return finish(answer, "tool_error")
            return finish(answer, "ok")

        results = []
        for block in [b for b in resp.content if b.type == "tool_use"]:
            output = dispatch(block.name, block.input)
            step = {"turn": turn, "tool": block.name, "input": block.input,
                    "output": output, "failed": "error" in output}
            trace.append(step)
            if step["failed"]:
                failures.append({"tool": block.name, "error": output["error"]})
            if on_step:
                on_step(step)
            results.append({"type": "tool_result", "tool_use_id": block.id,
                            "content": json.dumps(output, ensure_ascii=False),
                            "is_error": step["failed"]})

        messages.append({"role": "assistant", "content": resp.content})
        messages.append({"role": "user", "content": results})

    messages[-1]["content"].append({"type": "text", "text": EXHAUSTED_NUDGE})
    try:
        resp = call(model=config.MODEL, max_tokens=config.MAX_TOKENS,
                    system=system, messages=messages)
        answer = _text(resp) or EXHAUSTED_FALLBACK
    except Exception:
        answer = EXHAUSTED_FALLBACK

    return finish(answer, "turns_exhausted", limit=max_turns)

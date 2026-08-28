import time

from anthropic import Anthropic

import config
from core.agent import run_agent
from domain.tools import finance_tools, policy_tools
from domain.tools import tools as combined_tools

CATEGORIES = ("finance", "policy", "other")

ROUTER_SYSTEM = """Класифікуй запит клієнта monobank рівно в одну категорію.
finance — про власні гроші: витрати, надходження, баланс, конкретні операції за рахунком.
policy — про умови, тарифи, комісії, ліміти чи правила банку або будь-якого сервісу.
other — усе інше: привітання, питання про самого агента, не по темі.
Відповідай рівно одним словом: finance, policy або other."""

WORKERS = {
    "finance": lambda variant, rag: (config.finance_prompt(), finance_tools(variant)),
    "policy": lambda variant, rag: (config.policy_prompt(), policy_tools(rag)),
    "other": lambda variant, rag: (config.other_prompt(), []),
}


def classify(query):
    started = time.time()
    try:
        client = Anthropic(api_key=config.ANTHROPIC_API_KEY,
                           base_url=config.ANTHROPIC_BASE_URL or None)
        resp = client.messages.create(model=config.ROUTER_MODEL, max_tokens=20,
                                      thinking={"type": "disabled"},
                                      system=ROUTER_SYSTEM,
                                      messages=[{"role": "user", "content": query}])
        label = "".join(b.text for b in resp.content if b.type == "text").strip().lower()
        usage = {"in": resp.usage.input_tokens, "out": resp.usage.output_tokens, "calls": 1}
    except Exception as e:
        return "both", {"in": 0, "out": 0, "calls": 0}, round(time.time() - started, 2), str(e)

    label = label if label in CATEGORIES else "both"
    return label, usage, round(time.time() - started, 2), None


def run(query, variant=None, rag=None, max_turns=None, on_step=None):
    label, router_usage, router_sec, router_error = classify(query)
    variant = variant or config.TOOLS_VARIANT
    rag = rag or config.RAG_VARIANT

    if label == "both":
        system, worker_tools = config.system_prompt(rag), combined_tools(variant, rag)
    else:
        system, worker_tools = WORKERS[label](variant, rag)

    result = run_agent(query, worker_tools, system=system,
                       max_turns=max_turns, on_step=on_step)

    result["route"] = label
    result["route_error"] = router_error
    result["usage"]["in"] += router_usage["in"]
    result["usage"]["out"] += router_usage["out"]
    result["usage"]["calls"] += router_usage["calls"]
    result["elapsed_sec"] = round(result["elapsed_sec"] + router_sec, 2)
    return result

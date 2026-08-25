import json
import re

CITATION = re.compile(r"п(?:унктах?|ункт[ауіи]?|п)?\.?\s*(\d+(?:\.\d+)+)", re.IGNORECASE)
NUMBER = re.compile(r"\d[\d\s ]*(?:[.,]\d+)?")
ARITHMETIC_TOOLS = {"get_statement"}
DOC_TOOLS = {"search_docs"}


def _normalise(raw):
    body = raw.replace(" ", " ").replace(",", ".")
    return body.rstrip(".")


def _numbers(text):
    return {_normalise(match.group().replace(" ", "")) for match in NUMBER.finditer(text)}


def _haystack(trace):
    return json.dumps([step["output"] for step in trace], ensure_ascii=False)


def answer(text, trace):
    if not trace:
        return {"grounded": False,
                "note": "жоден інструмент не викликався — звіряти немає з чим"}

    used = {step["tool"] for step in trace}
    if not used & DOC_TOOLS:
        return None

    source = _haystack(trace)
    cited = sorted({match.group(1) for match in CITATION.finditer(text)})
    unknown_clauses = [clause for clause in cited if clause not in source]

    checks = {"grounded": True, "citations": len(cited),
              "unknown_citations": unknown_clauses}

    if used & ARITHMETIC_TOOLS:
        checks["figures"] = "пропущено: у прогоні є підрахунки за випискою"
    else:
        prose = CITATION.sub(" ", text)
        known = _numbers(source)
        unknown = sorted(value for value in _numbers(prose) if value not in known)
        checks["figures"] = len(_numbers(prose))
        checks["unknown_figures"] = unknown

    checks["ok"] = not unknown_clauses and not checks.get("unknown_figures")
    return checks

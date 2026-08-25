import json
import math
import re
from collections import Counter

import numpy as np

import config
from core import embed

INDEX = config.KNOWLEDGE / ".index"
CHUNKS = INDEX / "chunks.json"
VECTORS = INDEX / "vectors.npy"
META = INDEX / "meta.json"

CLAUSE = re.compile(r"^(\d{1,2}(?:\.\d{1,3}){1,4})\.?\s")
PARA_START = re.compile(r"^(?:\d{1,2}(?:\.\d{1,3}){0,4}\.?\s|Стаття\s|Розділ\s|[IVX]{1,4}\.\s|●\s)")
WORD = re.compile(r"[\w’'-]{3,}", re.UNICODE)
SENTENCE_BREAK = re.compile(r"(?<=[.!?;])\s+(?=[«\"(\[0-9А-ЯІЇЄҐA-Z])")
NUMBERING = re.compile(r"\d+(?:\.\d+)+")
ABBREVIATIONS = frozenset("п пп ст стст ч чч абз розд гл рис дод грн дол євро тис млн "
                          "млрд коп м вул буд кв обл смт р рр т ім проф акц напр див".split())

_cache = {}


def read_docs():
    docs = []
    for path in sorted(config.KNOWLEDGE.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        head, _, body = raw.partition("\n---\n")
        front = {}
        for line in head.lstrip("-\n").splitlines():
            key, _, value = line.partition(": ")
            if key:
                front[key.strip()] = value.strip()
        docs.append({**front, "text": body.strip()})
    return docs


def paragraphs(text):
    out, buf = [], []
    for line in [l.strip() for l in text.split("\n") if l.strip()]:
        if buf and PARA_START.match(line):
            out.append(" ".join(buf))
            buf = []
        buf.append(line)
    if buf:
        out.append(" ".join(buf))
    return out


def sentences(text):
    out, start = [], 0
    for match in SENTENCE_BREAK.finditer(text):
        head = text[start:match.start()]
        word = head.rstrip(".!?;").rsplit(" ", 1)[-1]
        if len(word) < 2 or word.lower() in ABBREVIATIONS or NUMBERING.fullmatch(word):
            continue
        out.append(head)
        start = match.end()
    out.append(text[start:])
    return [part for part in out if part.strip()]


def hard_cut(sentence):
    while len(sentence) > config.CHUNK_MAX:
        cut = sentence.rfind(" ", config.CHUNK_MAX // 2, config.CHUNK_MAX)
        cut = cut if cut > 0 else config.CHUNK_MAX
        yield sentence[:cut].strip()
        sentence = sentence[cut:].lstrip()
    yield sentence


def units(text):
    for number, para in enumerate(paragraphs(text)):
        found = CLAUSE.match(para)
        clause = found.group(1) if found else None
        if len(para) <= config.CHUNK_CHARS:
            yield para, clause, None
            continue
        buf, size = [], 0
        for sentence in sentences(para):
            for piece in hard_cut(sentence):
                if size and size + len(piece) > config.CHUNK_CHARS:
                    yield " ".join(buf), clause, number
                    buf, size = [], 0
                buf.append(piece)
                size += len(piece)
        if buf:
            yield " ".join(buf), clause, number


def split(text):
    parts, buf, size, clause, parent = [], [], 0, None, None
    for unit, unit_clause, unit_parent in units(text):
        if size and size + len(unit) > config.CHUNK_CHARS:
            parts.append(("\n".join(buf), clause, parent))
            buf, size, clause, parent = [], 0, None, None
        if buf and unit_parent != parent:
            parent = None
        elif not buf:
            parent = unit_parent
        buf.append(unit)
        size += len(unit)
        clause = clause or unit_clause
    if buf:
        parts.append(("\n".join(buf), clause, parent))
    return parts


def chunks_of(doc):
    return [{"doc": doc["id"], "title": doc["title"], "source": doc["source"],
             "effective_from": doc.get("effective_from"), "clause": clause,
             "parent": parent, "part": i, "text": text}
            for i, (text, clause, parent) in enumerate(split(doc["text"]))]


def build(verbose=True):
    docs = read_docs()
    if not docs:
        raise RuntimeError(f"У {config.KNOWLEDGE} немає документів — спершу fetch_knowledge.py")
    chunks = [c for doc in docs for c in chunks_of(doc)]
    if verbose:
        print(f"Документів: {len(docs)} · фрагментів: {len(chunks)} · "
              f"модель: {config.EMBED_MODEL}")
    vectors = embed.passages([c["text"] for c in chunks])
    INDEX.mkdir(parents=True, exist_ok=True)
    CHUNKS.write_text(json.dumps(chunks, ensure_ascii=False), encoding="utf-8")
    np.save(VECTORS, vectors)
    META.write_text(json.dumps({"model": config.EMBED_MODEL, "chunks": len(chunks),
                                "docs": len(docs), "dim": int(vectors.shape[1]),
                                "chunk_chars": config.CHUNK_CHARS},
                               ensure_ascii=False, indent=2), encoding="utf-8")
    _cache.clear()
    if verbose:
        print(f"Індекс збережено: {INDEX}")
    return len(chunks)


def index():
    if not _cache:
        if not CHUNKS.exists():
            raise RuntimeError("Індексу немає — запустити: python search.py --build")
        meta = json.loads(META.read_text(encoding="utf-8"))
        if meta["model"] != config.EMBED_MODEL:
            raise RuntimeError(f"Індекс побудований моделлю {meta['model']}, "
                               f"а зараз задана {config.EMBED_MODEL} — перебудувати індекс")
        _cache["chunks"] = json.loads(CHUNKS.read_text(encoding="utf-8"))
        _cache["vectors"] = np.load(VECTORS)
        _cache["bm25"] = _bm25_stats(_cache["chunks"])
    return _cache


def _bm25_stats(chunks):
    tokens = [Counter(WORD.findall(c["text"].lower())) for c in chunks]
    lengths = np.array([sum(t.values()) for t in tokens], dtype=np.float32)
    seen = Counter()
    for t in tokens:
        seen.update(t.keys())
    n = len(chunks)
    idf = {w: math.log(1 + (n - df + 0.5) / (df + 0.5)) for w, df in seen.items()}
    return {"tokens": tokens, "lengths": lengths, "idf": idf,
            "avg": float(lengths.mean()) if n else 0.0}


def semantic(query, top_k=None):
    data = index()
    scores = data["vectors"] @ embed.query(query)
    return _top(scores, data["chunks"], top_k or config.TOP_K)


def keyword(query, top_k=None):
    data = index()
    bm = data["bm25"]
    terms = WORD.findall(query.lower())
    k1, b = 1.5, 0.75
    scores = np.zeros(len(data["chunks"]), dtype=np.float32)
    for i, counts in enumerate(bm["tokens"]):
        norm = k1 * (1 - b + b * bm["lengths"][i] / (bm["avg"] or 1))
        total = 0.0
        for term in terms:
            tf = counts.get(term, 0)
            if tf:
                total += bm["idf"].get(term, 0.0) * tf * (k1 + 1) / (tf + norm)
        scores[i] = total
    return _top(scores, data["chunks"], top_k or config.TOP_K)


def _top(scores, chunks, top_k):
    out, seen = [], set()
    for i in np.argsort(-scores):
        chunk = chunks[i]
        body = " ".join(chunk["text"].split())
        if body in seen:
            continue
        seen.add(body)
        out.append({"score": round(float(scores[i]), 4), "position": int(i), **chunk})
        if len(out) == top_k:
            break
    return out


def _families():
    if "families" not in _cache:
        families = {}
        for i, chunk in enumerate(index()["chunks"]):
            if chunk["parent"] is not None:
                families.setdefault((chunk["doc"], chunk["parent"]), []).append(i)
        _cache["families"] = families
    return _cache["families"]


def expand(hit, budget=None):
    budget = budget or config.PARENT_CHARS
    family = _families().get((hit["doc"], hit["parent"]))
    if not family or len(family) < 2:
        return hit["text"], 1, len(family or [hit])
    chunks = index()["chunks"]
    first = last = family.index(hit["position"])
    total = len(chunks[family[first]]["text"])
    while True:
        grew = False
        if first > 0 and total + len(chunks[family[first - 1]]["text"]) <= budget:
            first -= 1
            total += len(chunks[family[first]]["text"])
            grew = True
        if last + 1 < len(family) and total + len(chunks[family[last + 1]]["text"]) <= budget:
            last += 1
            total += len(chunks[family[last]]["text"])
            grew = True
        if not grew:
            break
    text = " ".join(chunks[i]["text"] for i in family[first:last + 1])
    return text, last - first + 1, len(family)


def stats():
    return json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}

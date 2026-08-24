import argparse
import textwrap

import config
from domain import kb


def show(title, hits, min_score=None):
    print(f"\n{title}")
    if not hits or hits[0]["score"] <= 0:
        print("  — нічого не знайдено")
        return
    for i, hit in enumerate(hits, 1):
        clause = f" п. {hit['clause']}" if hit["clause"] else ""
        cut = "" if min_score is None or hit["score"] >= min_score else "  ↓ нижче порога"
        print(f"  {i}. [{hit['score']:.4f}] {hit['title']}{clause}{cut}")
        body = " ".join(hit["text"].split())[:260]
        print(textwrap.fill(body, width=96, initial_indent="     ", subsequent_indent="     "))


def main():
    parser = argparse.ArgumentParser(description="Пошук по базі документів monobank")
    parser.add_argument("query", nargs="?")
    parser.add_argument("--build", action="store_true", help="перебудувати індекс")
    parser.add_argument("--top", type=int, default=config.TOP_K)
    parser.add_argument("--only", choices=["keyword", "semantic"])
    args = parser.parse_args()

    if args.build:
        kb.build()
        return
    if not args.query:
        parser.error("потрібен запит або --build")

    meta = kb.stats()
    print(f"\nЗапит: «{args.query}»")
    print(f"База: {meta.get('docs')} документів, {meta.get('chunks')} фрагментів · "
          f"поріг схожості {config.MIN_SCORE}")
    if args.only != "semantic":
        show("Пошук по словах (BM25):", kb.keyword(args.query, args.top))
    if args.only != "keyword":
        show("Пошук по змісту (ембединги):", kb.semantic(args.query, args.top),
             config.MIN_SCORE)
    print()


if __name__ == "__main__":
    main()

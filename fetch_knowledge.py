import io
import json
import logging
import pathlib
import re
import sys
from datetime import date

import httpx
from pypdf import PdfReader

API = "https://monobank.ua/api/info/versioning-docs"
PDF = "https://monobank.ua/pdf"
PAGE = "https://monobank.ua"
OUT = pathlib.Path(__file__).parent / "knowledge"

SOURCES = [
    ("umovy", "terms", "Умови і правила обслуговування в АТ «Універсал Банк»"),
    ("taryfy", "rates", "Тарифи на банківські послуги monobank"),
    ("zminy-do-umov", "terms-changes", "Зміни до Умов і правил"),
    ("keshbek", "terms-cashback", "Умови нарахування кешбеку"),
    ("pasport-kredytnoi-kartky", "card-credit-characteristics",
     "Паспорт споживчого кредиту: кредитний ліміт на картці"),
    ("pasport-pokupka-chastynamy", "installment-characteristics",
     "Паспорт споживчого кредиту: Покупка частинами і Розстрочка"),
    ("pasport-do-zavtra", "kredyty-dozavra-characteristics",
     "Паспорт споживчого кредиту: Кредит «До завтра»"),
    ("monopay", "monopay-terms", "Умови сервісу monopay"),
    ("otrymannia-perekaziv", "receive-money-terms",
     "Умови отримання переказів (Shake to Pay)"),
    ("publichnyi-zbir", "dogovir-pro-publichnij-zbir",
     "Договір про публічний збір коштів (банка для зборів)"),
    ("restorany", "restaurants-terms", "Умови сервісу «Ресторани»"),
    ("zarplatnyi-proiekt", "payroll-terms", "Умови зарплатного проєкту"),
    ("yasno", "yasno-terms", "Умови сервісу Yasno"),
    ("obligatsii-taryfy", "bonds-tariffs", "Тарифи на операції з облігаціями"),
    ("obligatsii-dogovir", "bonds-agreement-public-part",
     "Договір про надання послуг з облігаціями: публічна частина"),
    ("obligatsii-depozytarii", "bonds-custodian-agreement-public-part",
     "Депозитарний договір: публічна частина"),
    ("invest-taryfy", "invest-tariffs", "Тарифи на інвестиційні послуги"),
    ("invest-dogovir", "invest-agreement-public-part",
     "Інвестиційний договір: публічна частина"),
]


def current_edition(slug):
    resp = httpx.get(f"{API}/{slug}", timeout=30,
                     headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True)
    resp.raise_for_status()
    editions = resp.json().get("result") or []
    if not editions:
        raise RuntimeError(f"{slug}: перелік редакцій порожній")
    return editions[0]


def unwrap_signature(raw):
    if raw.startswith(b"%PDF-"):
        return raw
    start = raw.find(b"%PDF-")
    if start < 0:
        raise RuntimeError("у контейнері немає PDF")
    end = raw.rfind(b"%%EOF")
    return raw[start:end + 5] if end > start else raw[start:]


def pdf_text(raw):
    reader = PdfReader(io.BytesIO(unwrap_signature(raw)))
    pages = [page.extract_text() or "" for page in reader.pages]
    return len(reader.pages), "\n".join(pages)


def tidy(text):
    text = text.replace(" ", " ").replace("‑", "-")
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        if re.fullmatch(r"\d{1,3}", line):
            continue
        lines.append(line)
    joined = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", joined).strip()


def write_doc(doc_id, page_slug, title, edition, pages, text):
    front = {"id": doc_id, "title": title, "page": f"{PAGE}/{page_slug}",
             "source": f"{PDF}/{edition['fileName']}",
             "effective_from": edition["dtFrom"], "pages": pages,
             "fetched": date.today().isoformat()}
    head = "\n".join(f"{k}: {v}" for k, v in front.items())
    (OUT / f"{doc_id}.md").write_text(f"---\n{head}\n---\n\n{text}\n", encoding="utf-8")
    return front


def main():
    logging.disable(logging.CRITICAL)
    OUT.mkdir(exist_ok=True)
    manifest = []
    for doc_id, slug, title in SOURCES:
        try:
            edition = current_edition(slug)
            raw = httpx.get(f"{PDF}/{edition['fileName']}", timeout=60,
                            headers={"User-Agent": "Mozilla/5.0"},
                            follow_redirects=True).content
            pages, text = pdf_text(raw)
            front = write_doc(doc_id, slug, title, edition, pages, tidy(text))
        except Exception as e:
            print(f"  ✗ {doc_id}: {type(e).__name__}: {e}", file=sys.stderr)
            continue
        manifest.append(front)
        print(f"  → {doc_id:28s} {front['effective_from']}  {pages:3d} с.  "
              f"{len(text):7d} знаків")
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nЗібрано документів: {len(manifest)}")


if __name__ == "__main__":
    main()

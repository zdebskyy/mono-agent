from typing import Annotated

from pydantic import Field

from mcp.server.mcpserver import MCPServer

from domain import mono

mcp = MCPServer("mono-tools")

_known_accounts: set[str] = set()


@mcp.tool()
def list_accounts() -> dict:
    """Крок 1 з 2 для будь-якого запиту про витрати, надходження або баланс.
    Повертає рахунки та банки клієнта monobank разом з їхніми id, валютою і балансом.
    id рахунку неможливо дізнатись жодним іншим способом."""
    resp = mono.client_info()
    if "error" in resp:
        return resp

    data = resp["data"]
    accounts = [{"id": a.get("id"),
                 "type": a.get("type"),
                 "currency": mono.CURRENCIES.get(a.get("currencyCode"), a.get("currencyCode")),
                 "balance_minor": a.get("balance"),
                 "masked_pan": (a.get("maskedPan") or [None])[0]}
                for a in data.get("accounts", [])]
    jars = [{"id": j.get("id"),
             "title": j.get("title"),
             "currency": mono.CURRENCIES.get(j.get("currencyCode"), j.get("currencyCode")),
             "balance_minor": j.get("balance"),
             "goal_minor": j.get("goal")}
            for j in data.get("jars", [])]

    _known_accounts.update(item["id"] for item in accounts + jars if item.get("id"))

    return {"accounts": accounts, "jars": jars,
            "note": "balance_minor — у копійках/центах, ділити на 100"}


@mcp.tool()
def get_statement(
    account: Annotated[str, Field(description=
        "id рахунку або банки, скопійований з відповіді list_accounts. "
        "Не назва картки, не валюта, не номер картки. Значення \"0\" "
        "(дефолтний рахунок) НЕ використовувати: у клієнта кілька рахунків "
        "у різних валютах, і дефолтний майже ніколи не є тим, про який питають.")],
    from_ts: Annotated[int, Field(description=
        "Початок періоду. Unix-час у СЕКУНДАХ (10 цифр), не мілісекунди і не рядок з датою.")],
    to_ts: Annotated[int, Field(description=
        "Кінець періоду, Unix-час у секундах. Максимальне вікно — 2682000 с "
        "(31 доба). Довший період розбивати на кілька викликів.")],
) -> dict:
    """Крок 2 з 2. Виписка по ОДНОМУ рахунку monobank за період.
    Викликати лише після list_accounts, взявши id звідти."""
    if account not in _known_accounts:
        return mono.fail("unknown_account",
                         f"account={account!r} не належить жодному рахунку цього клієнта",
                         hint="Спершу викликати list_accounts і взяти id звідти")

    resp = mono.statement(account, from_ts, to_ts)
    if "error" in resp:
        return resp

    raw = resp["data"]
    items = [{"time": t["time"], "description": t.get("description"),
              "amount_minor": t.get("amount"), "mcc": t.get("mcc")}
             for t in raw[:150]]

    return {"account": account, "count": len(items), "transactions": items,
            "note": "amount_minor — у копійках, відʼємне значення = витрата; "
                    "time — Unix-час у секундах"}


if __name__ == "__main__":
    mcp.run()

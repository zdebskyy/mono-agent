import argparse

import config
from core import report
from core.agent import run_agent
from core.router import run as run_router
from domain.tools import tools

DEFAULT_QUERY = "Скільки я витратив учора?"


def main():
    parser = argparse.ArgumentParser(description="Агент по рахунках monobank")
    parser.add_argument("query", nargs="?", default=DEFAULT_QUERY)
    parser.add_argument("--tools", choices=["v1", "v2"], default=config.TOOLS_VARIANT)
    parser.add_argument("--rag", choices=["naive", "guarded"], default=config.RAG_VARIANT,
                        help="naive — без порога і правил, guarded — з ними")
    parser.add_argument("--max-turns", type=int, default=config.MAX_TURNS)
    parser.add_argument("--model", default=config.MODEL)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--mask", action="store_true",
                        help="приховати суми та id — для прогонів у README")
    parser.add_argument("--router", action="store_true",
                        help="маршрутизатор: класифікує запит і веде до вузького спеціаліста "
                             "(FINANCE/POLICY/OTHER) замість одного агента з усіма інструментами")
    args = parser.parse_args()

    config.MODEL = args.model
    config.RAG_VARIANT = args.rag
    report.header(args.query, args.model, args.tools, args.max_turns, args.rag)
    if args.router:
        result = run_router(args.query, variant=args.tools, rag=args.rag,
                            max_turns=args.max_turns,
                            on_step=report.stepper(args.mask, args.verbose))
        report.route(result["route"], result["route_error"])
    else:
        result = run_agent(args.query, tools(args.tools), system=config.system_prompt(args.rag),
                           max_turns=args.max_turns,
                           on_step=report.stepper(args.mask, args.verbose))
    report.summary(result, args.mask)


if __name__ == "__main__":
    main()

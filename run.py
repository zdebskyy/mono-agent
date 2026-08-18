import argparse

import config
from core import report
from core.agent import run_agent
from domain.tools import tools

DEFAULT_QUERY = "Скільки я витратив учора?"


def main():
    parser = argparse.ArgumentParser(description="Агент по рахунках monobank")
    parser.add_argument("query", nargs="?", default=DEFAULT_QUERY)
    parser.add_argument("--tools", choices=["v1", "v2"], default=config.TOOLS_VARIANT)
    parser.add_argument("--max-turns", type=int, default=config.MAX_TURNS)
    parser.add_argument("--model", default=config.MODEL)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--mask", action="store_true",
                        help="приховати суми та id — для прогонів у README")
    args = parser.parse_args()

    config.MODEL = args.model
    report.header(args.query, args.model, args.tools, args.max_turns)
    result = run_agent(args.query, tools(args.tools), max_turns=args.max_turns,
                       on_step=report.stepper(args.mask, args.verbose))
    report.summary(result, args.mask)


if __name__ == "__main__":
    main()

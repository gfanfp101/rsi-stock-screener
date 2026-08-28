from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from rsi_screener.providers import MassiveProvider
from rsi_screener.screener import screen_histories
from rsi_screener.storage import PriceStore


def _business_days(end: date, count: int) -> list[date]:
    days: list[date] = []
    current = end
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)
        current -= timedelta(days=1)
    return list(reversed(days))


def fetch(args: argparse.Namespace) -> None:
    provider = MassiveProvider(
        os.environ.get("MASSIVE_API_KEY", ""),
        base_url=os.environ.get("MASSIVE_BASE_URL", "https://api.massive.com"),
    )
    rpm = float(os.environ.get("MASSIVE_REQUESTS_PER_MINUTE", "5"))
    delay = 60.0 / rpm if rpm > 0 else 0.0
    with PriceStore(args.database) as store:
        requested = _business_days(date.fromisoformat(args.end), args.days)
        pending = [day for day in requested if not store.has_day(day)]
        for number, day in enumerate(pending, 1):
            bars = provider.daily_market(day)
            saved = store.save(bars)
            print(f"{day}: saved {saved:,} bars ({number}/{len(pending)})")
            if number < len(pending) and delay:
                time.sleep(delay)


def screen(args: argparse.Namespace) -> None:
    with PriceStore(args.database) as store:
        results = screen_histories(store.histories(limit=args.history))
    output = sys.stdout if args.output == "-" else open(args.output, "w", newline="")
    try:
        writer = csv.writer(output)
        writer.writerow(["ticker", "crossed_on", "reached_60_on", "days_to_60", "latest_rsi"])
        for item in results:
            writer.writerow([
                item.ticker,
                item.crossed_on.isoformat(),
                item.reached_60_on.isoformat(),
                item.days_to_60,
                f"{item.latest_rsi:.2f}",
            ])
    finally:
        if output is not sys.stdout:
            output.close()
    if args.output != "-":
        print(f"Wrote {len(results)} matches to {args.output}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Daily RSI momentum stock screener")
    parser.add_argument("--database", default="data/prices.sqlite3")
    commands = parser.add_subparsers(dest="command", required=True)
    fetch_parser = commands.add_parser("fetch", help="download grouped daily market bars")
    fetch_parser.add_argument("--end", default=date.today().isoformat())
    fetch_parser.add_argument("--days", type=int, default=120)
    fetch_parser.set_defaults(func=fetch)
    screen_parser = commands.add_parser("screen", help="screen locally cached prices")
    screen_parser.add_argument("--history", type=int, default=160)
    screen_parser.add_argument("--output", default="-")
    screen_parser.set_defaults(func=screen)
    run_parser = commands.add_parser("run", help="fetch, then screen")
    run_parser.add_argument("--end", default=date.today().isoformat())
    run_parser.add_argument("--days", type=int, default=120)
    run_parser.add_argument("--history", type=int, default=160)
    run_parser.add_argument("--output", default="matches.csv")

    def run(args: argparse.Namespace) -> None:
        fetch(args)
        screen(args)

    run_parser.set_defaults(func=run)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        args.func(args)
    except (ValueError, RuntimeError) as error:
        raise SystemExit(f"error: {error}") from error


if __name__ == "__main__":
    main()

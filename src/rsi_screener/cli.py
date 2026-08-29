from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests import HTTPError
from datetime import date, timedelta
from pathlib import Path

from rsi_screener.providers import MassiveProvider
from rsi_screener.metadata import MetadataStore
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


def _weekdays_between(start: date, end: date) -> list[date]:
    days: list[date] = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def fetch(args: argparse.Namespace) -> None:
    provider = MassiveProvider(
        os.environ.get("MASSIVE_API_KEY", ""),
        base_url=os.environ.get("MASSIVE_BASE_URL", "https://api.massive.com"),
    )
    rpm = float(os.environ.get("MASSIVE_REQUESTS_PER_MINUTE", "5"))
    delay = 60.0 / rpm if rpm > 0 else 0.0
    with PriceStore(args.database) as store:
        end = date.fromisoformat(args.end)
        baseline = _business_days(end, args.days)
        latest = store.latest_day()
        start = baseline[0]
        if latest is not None and latest + timedelta(days=1) < start:
            start = latest + timedelta(days=1)
        requested = _weekdays_between(start, end)
        pending = [day for day in requested if not store.has_day(day)]
        for number, day in enumerate(pending, 1):
            bars = provider.daily_market(day)
            saved = store.save(bars)
            store.mark_day_downloaded(day, saved)
            print(f"{day}: saved {saved:,} bars ({number}/{len(pending)})")
            if number < len(pending) and delay:
                time.sleep(delay)


def screen(args: argparse.Namespace) -> None:
    metadata = None
    if args.min_market_cap is not None:
        with MetadataStore(args.metadata_database) as metadata_store:
            metadata = metadata_store.all()
    with PriceStore(args.database) as store:
        results = screen_histories(
            store.histories(limit=args.history), metadata=metadata,
            min_market_cap=args.min_market_cap,
        )
    output = sys.stdout if args.output == "-" else open(args.output, "w", newline="")
    try:
        writer = csv.writer(output)
        writer.writerow(["ticker", "market_cap", "pe_ratio", "sector", "industry",
                         "period_start", "period_end", "latest_rsi",
                         "start_average_rsi", "latest_average_rsi", "average_rsi_change"])
        for item in results:
            writer.writerow([
                item.ticker, f"{item.market_cap:.0f}" if item.market_cap else "",
                f"{item.pe_ratio:.2f}" if item.pe_ratio else "",
                item.sector or "", item.industry or "",
                item.period_start.isoformat(), item.period_end.isoformat(),
                f"{item.latest_rsi:.2f}",
                f"{item.start_average_rsi:.2f}", f"{item.latest_average_rsi:.2f}",
                f"{item.average_rsi_change:.4f}",
            ])
    finally:
        if output is not sys.stdout:
            output.close()
    if args.output != "-":
        print(f"Wrote {len(results)} matches to {args.output}")


def refresh_metadata(args: argparse.Namespace) -> None:
    provider = MassiveProvider(
        os.environ.get("MASSIVE_API_KEY", ""),
        base_url=os.environ.get("MASSIVE_BASE_URL", "https://api.massive.com"),
    )
    rpm = float(os.environ.get("MASSIVE_REQUESTS_PER_MINUTE", "5"))
    delay = 60.0 / rpm if rpm > 0 else 0.0
    with MetadataStore(args.metadata_database) as store:
        if args.force or not store.fundamentals_are_fresh(max_age_days=7):
            try:
                rows = provider.financial_ratios(request_delay=delay)
            except HTTPError as error:
                if error.response is None or error.response.status_code != 403 or not args.tickers_file:
                    raise
                print("Ratios entitlement unavailable; using ticker details for market cap.")
            else:
                print(f"Saved ratios for {store.save_ratios(rows):,} tickers")
        if args.tickers_file:
            with open(args.tickers_file, newline="") as source:
                tickers = [row["ticker"] for row in csv.DictReader(source)]
            active_common = provider.active_common_tickers()
            tickers = [ticker for ticker in tickers if ticker in active_common]
            missing = store.missing_classifications(tickers)
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                futures = {executor.submit(provider.ticker_details, ticker): ticker for ticker in missing}
                for index, future in enumerate(as_completed(futures), 1):
                    details = future.result()
                    store.save_details([details])
                    print(f"Saved details for {details.ticker} ({index}/{len(missing)})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Daily RSI momentum stock screener")
    parser.add_argument("--database", default="data/prices.sqlite3")
    parser.add_argument("--metadata-database", default="data/metadata.sqlite3")
    commands = parser.add_subparsers(dest="command", required=True)
    fetch_parser = commands.add_parser("fetch", help="download grouped daily market bars")
    fetch_parser.add_argument("--end", default=date.today().isoformat())
    fetch_parser.add_argument("--days", type=int, default=120)
    fetch_parser.set_defaults(func=fetch)
    screen_parser = commands.add_parser("screen", help="screen locally cached prices")
    screen_parser.add_argument("--history", type=int, default=160)
    screen_parser.add_argument("--output", default="-")
    screen_parser.add_argument("--min-market-cap", type=float)
    screen_parser.set_defaults(func=screen)
    run_parser = commands.add_parser("run", help="fetch, then screen")
    run_parser.add_argument("--end", default=date.today().isoformat())
    run_parser.add_argument("--days", type=int, default=120)
    run_parser.add_argument("--history", type=int, default=160)
    run_parser.add_argument("--output", default="matches.csv")
    run_parser.add_argument("--min-market-cap", type=float, default=1_000_000_000)

    def run(args: argparse.Namespace) -> None:
        fetch(args)
        screen(args)

    run_parser.set_defaults(func=run)
    metadata_parser = commands.add_parser("metadata-refresh", help="refresh weekly fundamentals cache")
    metadata_parser.add_argument("--tickers-file")
    metadata_parser.add_argument("--force", action="store_true")
    metadata_parser.add_argument("--workers", type=int, default=8)
    metadata_parser.set_defaults(func=refresh_metadata)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        args.func(args)
    except (ValueError, RuntimeError) as error:
        raise SystemExit(f"error: {error}") from error


if __name__ == "__main__":
    main()

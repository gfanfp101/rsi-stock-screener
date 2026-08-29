# RSI Stock Screener

A small, local-first screener for persistent RSI momentum in U.S. stocks. It
downloads split-adjusted end-of-day bars, caches them in SQLite, calculates
Wilder RSI(14), and exports qualifying tickers as CSV.

## Signal definition

1. Calculate daily Wilder RSI(14).
2. Calculate a 14-day simple moving average of RSI(14) for every trading day.
3. Across the latest 14 trading days, that RSI average must never decrease.
   Equal consecutive values are accepted.
4. The latest raw RSI(14) must be strictly above 65.
5. Rank matches by the average daily increase in the RSI average across the
   14-day trend window, largest first.

## Data architecture

The included provider uses Massive (formerly Polygon.io). Its grouped daily
endpoint returns OHLCV for the U.S. stock market for one date, which is much
more economical than one request per ticker. Provider access is isolated
behind `DataProvider`, so another vendor can be added without changing RSI,
storage, or screening logic. Downloaded bars are cached; repeat runs skip dates
already in SQLite.

The default fetch rate is five requests per minute to suit low-cost access.
Confirm the limits and historical access of your own plan. The initial 120-day
backfill can therefore take a while; daily updates need only one new request.

## Setup

Python 3.10 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
```

Put your Massive API key in `.env`, then load it into your shell. Never commit
`.env` or paste the key into an issue or chat.

```bash
set -a
source .env
set +a
```

## Run

Download approximately 120 weekdays (market holidays simply return no bars):

```bash
rsi-screener fetch --days 120 --end 2026-08-27
```

Screen the local cache and print CSV:

```bash
rsi-screener screen
```

Fetch missing days and write matches in one command:

```bash
rsi-screener run --days 120 --output matches.csv
```

## Weekly fundamentals and market-cap filter

Fundamentals are stored separately in `data/metadata.sqlite3`. The Massive
Financials & Ratios Expansion is required. Refresh market cap and trailing P/E
weekly, then screen for companies worth at least $1 billion. Results are ranked
by market cap, descending:

```bash
rsi-screener metadata-refresh
rsi-screener screen --min-market-cap 1000000000 --output matches.csv
```

Sector and industry classifications change infrequently. Enrich only current
matches, and the cache will skip tickers already classified:

```bash
rsi-screener metadata-refresh --tickers-file matches.csv
```

Use `--database path/to/prices.sqlite3` before the subcommand to choose another
database. Set `MASSIVE_REQUESTS_PER_MINUTE` if your plan permits a different
rate, or `MASSIVE_BASE_URL` for a compatible gateway.

## Test

```bash
pytest
# Or, without installing development dependencies:
PYTHONPATH=src python -m unittest discover -s tests
```

Tests cover the Wilder calculation, threshold equality, the 30-day boundary,
the 60-observation window, failed holds, later valid sequences, and provider
response mapping.

## GitHub authentication

Do **not** share a private SSH key. Prefer GitHub's browser/device OAuth flow,
or create a fine-grained token stored in your operating system's credential
manager. Grant only the repository permissions needed. Once authenticated:

```bash
git init
git add .
git commit -m "Initial RSI stock screener"
git branch -M main
git remote add origin https://github.com/YOUR_ACCOUNT/rsi-stock-screener.git
git push -u origin main
```

## Notes

- This project is for research, not investment advice.
- A full-universe result may include ETFs, ADRs, preferred shares, and other
  exchange-listed instruments. Add a reference-data filter if you want only
  active common stocks.
- Scheduled daily execution can be added after the first successful backfill.

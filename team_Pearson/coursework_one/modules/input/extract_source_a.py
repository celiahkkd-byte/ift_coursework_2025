"""
extract_source_a.py
====================
Extractor A — Main data source access and raw data dumping to MinIO.

This module is responsible for:
1. Connecting to Alpha Vantage (financial data API)
2. Downloading 5+ years of daily stock price data per company
3. Saving raw data to MinIO at the path:
   raw/source_a/{TICKER}/as_of={DATE}/run_date={DATE}/data.json

How to run directly:
    poetry run python modules/input/extract_source_a.py
    poetry run python modules/input/extract_source_a.py --run-date 2024-01-01
    poetry run python modules/input/extract_source_a.py --years-back 7

How to import into another module:
    from modules.input.extract_source_a import extract_source_a
    results = extract_source_a(["AAPL", "MSFT"], "2024-02-13", 5, "daily")
"""

import logging
import time
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any, Dict, List

import pandas as pd
import requests
import yaml
from minio import Minio

# ---------------------------------------------------------------------------
# LOGGING SETUP
# Prints timestamped messages to the terminal so you can see what's happening.
# Example output: 2024-11-15 10:23:01 [INFO] Fetching data for AAPL...
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CONFIG LOADER
# ---------------------------------------------------------------------------

def load_config(config_path: str = "config/conf.yaml") -> dict:
    """
    Reads the YAML configuration file and returns it as a dictionary.

    All settings (API keys, company list, MinIO credentials) live in
    conf.yaml so we never hardcode secrets directly in the code.

    :param config_path: Relative path to the config file.
    :return: Dictionary of all configuration values.

    Example:
        config = load_config()
        api_key = config["api"]["alpha_vantage_key"]
    """
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    logger.info(f"Config loaded from: {config_path}")
    return config


# ---------------------------------------------------------------------------
# ALPHA VANTAGE — DATA FETCHER
# ---------------------------------------------------------------------------

def fetch_daily_data(ticker: str, api_key: str) -> pd.DataFrame:
    """
    Downloads the complete daily price history for one company from Alpha Vantage.

    Uses the TIME_SERIES_DAILY endpoint with outputsize=full, which returns
    20+ years of open, high, low, close, and volume data.

    :param ticker: Stock ticker symbol, e.g. "AAPL" for Apple.
    :param api_key: Alpha Vantage API key from conf.yaml.
    :return: DataFrame indexed by date with columns: open, high, low, close, volume.

    :raises ValueError: If the ticker is invalid or the rate limit is hit.
    :raises requests.HTTPError: If the network request fails.

    Example:
        df = fetch_daily_data("AAPL", api_key="YOUR_KEY")
    """
    logger.info(f"Fetching data for {ticker} from Alpha Vantage...")

    url = (
        "https://www.alphavantage.co/query"
        "?function=TIME_SERIES_DAILY"
        f"&symbol={ticker}"
        "&outputsize=full"
        f"&apikey={api_key}"
    )

    response = requests.get(url, timeout=30)
    response.raise_for_status()
    raw_json = response.json()

    # Handle known Alpha Vantage error responses
    if "Error Message" in raw_json:
        raise ValueError(
            f"Alpha Vantage rejected ticker '{ticker}': {raw_json['Error Message']}"
        )
    if "Note" in raw_json:
        raise ValueError(
            f"Alpha Vantage rate limit reached. Try again later. Detail: {raw_json['Note']}"
        )
    if "Information" in raw_json:
        raise ValueError(
            f"Alpha Vantage API key issue: {raw_json['Information']}"
        )
    if "Time Series (Daily)" not in raw_json:
        raise ValueError(
            f"Unexpected Alpha Vantage response for '{ticker}': {raw_json}"
        )

    # Parse the time series into a clean DataFrame
    time_series = raw_json["Time Series (Daily)"]
    df = pd.DataFrame.from_dict(time_series, orient="index")

    # Rename columns from "1. open" style to clean "open" style
    df.columns = ["open", "high", "low", "close", "volume"]

    # Set index as proper datetime and sort oldest to newest
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    df.sort_index(inplace=True)

    # Convert all values from strings to numbers
    for col in df.columns:
        df[col] = pd.to_numeric(df[col])

    logger.info(
        f"  Retrieved {len(df)} trading days for {ticker} "
        f"({df.index.min().date()} to {df.index.max().date()})"
    )
    return df


def filter_to_date_range(
    df: pd.DataFrame,
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """
    Filters a DataFrame to only include rows within a given date range.

    :param df: Full DataFrame from fetch_daily_data().
    :param start_date: Start of range as "YYYY-MM-DD", e.g. "2019-01-01".
    :param end_date: End of range as "YYYY-MM-DD", e.g. "2024-12-31".
    :return: Filtered DataFrame containing only dates within the range.

    Example:
        filtered = filter_to_date_range(df, "2019-01-01", "2024-12-31")
    """
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    filtered = df.loc[(df.index >= start) & (df.index <= end)]
    logger.info(
        f"  Filtered to {len(filtered)} rows "
        f"between {start_date} and {end_date}"
    )
    return filtered


# ---------------------------------------------------------------------------
# MINIO — STORAGE
# ---------------------------------------------------------------------------

def get_minio_client(config: dict) -> Minio:
    """
    Creates and returns a connected MinIO client.

    MinIO is the object storage system used as our data lake.
    It runs locally in Docker and stores raw data files in buckets.

    :param config: Config dictionary from load_config().
    :return: Connected Minio client object.

    Example:
        client = get_minio_client(config)
    """
    cfg = config["minio"]
    client = Minio(
        endpoint=cfg["endpoint"],
        access_key=cfg["access_key"],
        secret_key=cfg["secret_key"],
        secure=cfg.get("secure", False),
    )
    logger.info(f"Connected to MinIO at {cfg['endpoint']}")
    return client


def ensure_bucket_exists(client: Minio, bucket_name: str) -> None:
    """
    Creates a MinIO bucket if it does not already exist.

    A bucket is the top-level container in MinIO (like a root folder).
    All raw data for this project lives inside one bucket.

    :param client: Connected Minio client from get_minio_client().
    :param bucket_name: Name of the bucket, e.g. "data-lake".

    Example:
        ensure_bucket_exists(client, "data-lake")
    """
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
        logger.info(f"Created MinIO bucket: '{bucket_name}'")
    else:
        logger.info(f"MinIO bucket '{bucket_name}' already exists")


def save_to_minio(
    client: Minio,
    bucket_name: str,
    ticker: str,
    df: pd.DataFrame,
    as_of_date: str,
    run_date: str,
) -> str:
    """
    Saves a company's price DataFrame as a JSON file in MinIO.

    Files are stored at this structured path inside the bucket:
        raw/source_a/{TICKER}/as_of={AS_OF_DATE}/run_date={RUN_DATE}/data.json

    Example path:
        raw/source_a/AAPL/as_of=2024-02-13/run_date=2024-02-13/data.json

    Path structure explained:
        raw/        — untouched, unprocessed data
        source_a/   — data from Alpha Vantage (Source A)
        as_of=      — the latest date covered by this data
        run_date=   — the date this pipeline actually ran

    :param client: Connected Minio client.
    :param bucket_name: Target bucket name.
    :param ticker: Company ticker symbol, e.g. "AAPL".
    :param df: DataFrame to save (from filter_to_date_range).
    :param as_of_date: Latest date in the data, e.g. "2024-02-13".
    :param run_date: Date the pipeline was executed, e.g. "2024-02-13".
    :return: The full object path inside the bucket where data was saved.

    Example:
        path = save_to_minio(client, "data-lake", "AAPL", df,
                             as_of_date="2024-02-13", run_date="2024-02-13")
    """
    object_path = (
        f"raw/source_a/{ticker}/"
        f"as_of={as_of_date}/"
        f"run_date={run_date}/"
        f"data.json"
    )

    # Convert DataFrame to JSON bytes for upload
    df_copy = df.reset_index()
    df_copy["date"] = df_copy["date"].astype(str)
    json_bytes = df_copy.to_json(orient="records", indent=2).encode("utf-8")

    client.put_object(
        bucket_name=bucket_name,
        object_name=object_path,
        data=BytesIO(json_bytes),
        length=len(json_bytes),
        content_type="application/json",
    )

    logger.info(f"  Saved to MinIO: {bucket_name}/{object_path}")
    return object_path


# ---------------------------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------------------------

def run_extraction(
    config_path: str = "config/conf.yaml",
    run_date: str = None,
    years_back: int = 5,
) -> list:
    """
    Runs the full Extractor A pipeline end-to-end.

    For each company in conf.yaml, this function:
        1. Fetches full daily price history from Alpha Vantage
        2. Filters to the required date range (default: 5 years back)
        3. Saves the raw data as JSON to MinIO

    If one company fails (e.g. bad ticker, rate limit), it logs the error
    and continues processing the remaining companies.

    :param config_path: Path to conf.yaml. Default: "config/conf.yaml".
    :param run_date: Date to run as (YYYY-MM-DD). Defaults to today.
    :param years_back: Years of history to capture. Default: 5.
    :return: List of MinIO object paths where data was successfully saved.

    Example:
        # Standard run (today's date, 5 years back)
        paths = run_extraction()

        # Backfill run for a specific date
        paths = run_extraction(run_date="2024-01-01", years_back=7)
    """
    # Set run_date to today if not provided
    if run_date is None:
        run_date = datetime.today().strftime("%Y-%m-%d")

    # Calculate the start date (years_back years before run_date)
    run_dt = datetime.strptime(run_date, "%Y-%m-%d")
    start_date = (run_dt - timedelta(days=365 * years_back)).strftime("%Y-%m-%d")
    end_date = run_date

    logger.info("=" * 60)
    logger.info("EXTRACTOR A — Alpha Vantage -> MinIO Pipeline")
    logger.info(f"  Run date  : {run_date}")
    logger.info(f"  Backfill  : {start_date} to {end_date} ({years_back} years)")
    logger.info("=" * 60)

    config = load_config(config_path)
    api_key = config["api"]["alpha_vantage_key"]
    companies = config["companies"]
    bucket_name = config["minio"]["bucket"]

    minio_client = get_minio_client(config)
    ensure_bucket_exists(minio_client, bucket_name)

    saved_paths = []

    for i, ticker in enumerate(companies):
        logger.info(f"\n[{i + 1}/{len(companies)}] Processing {ticker}...")

        try:
            full_df = fetch_daily_data(ticker, api_key)
            filtered_df = filter_to_date_range(full_df, start_date, end_date)

            if filtered_df.empty:
                logger.warning(
                    f"  No data for {ticker} between {start_date} and {end_date} — skipping"
                )
                continue

            path = save_to_minio(
                client=minio_client,
                bucket_name=bucket_name,
                ticker=ticker,
                df=filtered_df,
                as_of_date=end_date,
                run_date=run_date,
            )
            saved_paths.append(path)
            logger.info(f"  [OK] {ticker} saved successfully")

        except ValueError as e:
            logger.error(f"  [SKIP] {ticker} — {e}")

        except Exception as e:
            logger.error(f"  [ERROR] {ticker} — Unexpected error: {e}")

        finally:
            # Respect Alpha Vantage free tier limit (~5 requests/minute)
            # Wait 12 seconds between each company request
            if i < len(companies) - 1:
                logger.info("  Waiting 12s (API rate limit)...")
                time.sleep(12)

    logger.info("\n" + "=" * 60)
    logger.info(
        f"Pipeline complete: {len(saved_paths)}/{len(companies)} companies saved to MinIO"
    )
    logger.info("=" * 60)

    return saved_paths


# ---------------------------------------------------------------------------
# INTEGRATION WRAPPER
# This function provides the standardized interface expected by the team's
# integration layer while using our internal pipeline implementation.
# ---------------------------------------------------------------------------

def extract_source_a(
    symbols: List[str],
    run_date: str,
    backfill_years: int,
    frequency: str
) -> List[Dict[str, Any]]:
    """
    Integration wrapper for the main extraction pipeline.
    
    This function matches the team's integration contract: it accepts
    a standardized set of parameters and returns metadata about the
    extraction in a standardized format.
    
    NOTE: The actual data is saved to MinIO as raw JSON files. This function
    returns metadata about what was extracted, not the data itself.
    
    :param symbols: List of stock ticker symbols (e.g. ["AAPL", "MSFT"]).
                    Currently ignored — symbols are read from conf.yaml instead.
    :param run_date: Date to run the extraction for, format "YYYY-MM-DD".
    :param backfill_years: Number of years of historical data to fetch (default: 5).
    :param frequency: Data frequency. Alpha Vantage only provides "daily" data.
    :return: List of dictionaries with standardized metadata format.
    
    Example:
        results = extract_source_a(
            symbols=["AAPL", "MSFT"],
            run_date="2024-02-13",
            backfill_years=5,
            frequency="daily"
        )
    """
    logger.info("=" * 60)
    logger.info("INTEGRATION WRAPPER — extract_source_a() called")
    logger.info(f"  Requested symbols: {symbols}")
    logger.info(f"  Run date: {run_date}")
    logger.info(f"  Backfill years: {backfill_years}")
    logger.info(f"  Frequency: {frequency}")
    logger.info("=" * 60)
    
    # Note: We read the actual symbol list from conf.yaml, not from the parameter
    # This is documented in the handover notes
    config = load_config("config/conf.yaml")
    actual_symbols = config["companies"]
    
    logger.info(f"NOTE: Using symbols from conf.yaml: {actual_symbols}")
    logger.info(f"(Ignoring function parameter symbols: {symbols})")
    
    # Run the main extraction pipeline
    # This saves raw JSON data to MinIO and returns the storage paths
    saved_paths = run_extraction(
        config_path="config/conf.yaml",
        run_date=run_date,
        years_back=backfill_years
    )
    
    # Build the standardized return format expected by the integration layer
    # Each symbol gets one metadata record
    results = []
    for symbol in actual_symbols:
        results.append({
            "symbol": symbol,
            "observation_date": run_date,
            "factor_name": "daily_price_data",
            "factor_value": float(len(saved_paths)),  # Number of companies successfully processed
            "source": "alpha_vantage",
            "metric_frequency": "daily",  # Alpha Vantage only provides daily data
        })
    
    logger.info(f"\nReturning metadata for {len(results)} symbols")
    return results


# ---------------------------------------------------------------------------
# ENTRY POINT
# Runs only when this file is executed directly (not when imported).
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Extractor A: Fetch stock data from Alpha Vantage and save to MinIO"
    )
    parser.add_argument(
        "--run-date",
        type=str,
        default=None,
        help="Date to run the pipeline for (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--years-back",
        type=int,
        default=5,
        help="Number of years of historical data to fetch. Default: 5",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/conf.yaml",
        help="Path to the config file. Default: config/conf.yaml",
    )

    args = parser.parse_args()

    run_extraction(
        config_path=args.config,
        run_date=args.run_date,
        years_back=args.years_back,
    )

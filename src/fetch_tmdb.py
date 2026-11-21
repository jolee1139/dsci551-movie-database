import argparse
import json
import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SELECTED_MOVIES_PATH = (
    PROJECT_ROOT / "data" / "staging" / "top_5000_movies.csv"
)
CACHE_DIR = PROJECT_ROOT / "data" / "tmdb_cache"
FAILURES_PATH = (
    PROJECT_ROOT / "data" / "staging" / "tmdb_fetch_failures.csv"
)

API_BASE_URL = "https://api.themoviedb.org/3/movie"

REQUEST_DELAY = 0.1
MAX_RETRIES = 5


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Fetch and cache TMDB movie details."
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Fetch only the first N movies for testing.",
    )

    return parser.parse_args()


def load_tmdb_ids(limit=None):
    if not SELECTED_MOVIES_PATH.exists():
        raise FileNotFoundError(
            "top_5000_movies.csv was not found. "
            "Run profile_and_select.py first."
        )

    movies = pd.read_csv(
        SELECTED_MOVIES_PATH,
        dtype={
            "movieId": "int32",
            "tmdbId": "Int64",
        },
    )

    tmdb_ids = (
        movies["tmdbId"]
        .dropna()
        .astype("int64")
        .drop_duplicates()
        .tolist()
    )

    if limit is not None:
        tmdb_ids = tmdb_ids[:limit]

    return tmdb_ids


def cache_is_valid(cache_path, tmdb_id):
    if not cache_path.exists():
        return False

    try:
        cached_data = json.loads(
            cache_path.read_text(encoding="utf-8")
        )
        return cached_data.get("id") == tmdb_id
    except (json.JSONDecodeError, OSError):
        return False


def save_to_cache(cache_path, movie_data):
    temporary_path = cache_path.with_suffix(".json.tmp")

    temporary_path.write_text(
        json.dumps(movie_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    temporary_path.replace(cache_path)


def fetch_movie(session, tmdb_id):
    url = f"{API_BASE_URL}/{tmdb_id}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(
                url,
                params={"language": "en-US"},
                timeout=30,
            )
        except requests.RequestException as error:
            if attempt == MAX_RETRIES:
                return None, str(error)

            wait_time = 2 ** (attempt - 1)
            print(
                f"Network error for TMDB ID {tmdb_id}. "
                f"Retrying in {wait_time} seconds."
            )
            time.sleep(wait_time)
            continue

        if response.status_code == 200:
            return response.json(), None

        if response.status_code == 404:
            return None, "404: Movie not found"

        if response.status_code == 429:
            wait_time = int(response.headers.get("Retry-After", 5))
            print(
                f"Rate limited. Waiting {wait_time} seconds."
            )
            time.sleep(wait_time)
            continue

        if response.status_code >= 500:
            if attempt == MAX_RETRIES:
                return None, f"HTTP {response.status_code}"

            wait_time = 2 ** (attempt - 1)
            print(
                f"TMDB server error {response.status_code}. "
                f"Retrying in {wait_time} seconds."
            )
            time.sleep(wait_time)
            continue

        return None, f"HTTP {response.status_code}: {response.text[:200]}"

    return None, "Maximum retries exceeded"


def main():
    args = parse_arguments()

    load_dotenv()
    token = os.getenv("TMDB_BEARER_TOKEN")

    if not token:
        raise RuntimeError(
            "TMDB_BEARER_TOKEN was not found in .env."
        )

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    tmdb_ids = load_tmdb_ids(args.limit)

    downloaded = 0
    cached = 0
    failures = []

    print(f"Preparing to process {len(tmdb_ids):,} unique TMDB IDs.")

    with requests.Session() as session:
        session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "accept": "application/json",
            }
        )

        for position, tmdb_id in enumerate(tmdb_ids, start=1):
            cache_path = CACHE_DIR / f"{tmdb_id}.json"

            if cache_is_valid(cache_path, tmdb_id):
                cached += 1
            else:
                movie_data, error = fetch_movie(session, tmdb_id)

                if movie_data is not None:
                    save_to_cache(cache_path, movie_data)
                    downloaded += 1
                else:
                    failures.append(
                        {
                            "tmdbId": tmdb_id,
                            "error": error,
                        }
                    )

                time.sleep(REQUEST_DELAY)

            if position % 50 == 0 or position == len(tmdb_ids):
                print(
                    f"Processed {position:,}/{len(tmdb_ids):,} "
                    f"| downloaded: {downloaded:,} "
                    f"| cached: {cached:,} "
                    f"| failed: {len(failures):,}"
                )

    pd.DataFrame(
        failures,
        columns=["tmdbId", "error"],
    ).to_csv(FAILURES_PATH, index=False)

    print("\nTMDB fetching complete.")
    print(f"Downloaded: {downloaded:,}")
    print(f"Already cached: {cached:,}")
    print(f"Failed: {len(failures):,}")
    print(f"Cache directory: {CACHE_DIR}")


if __name__ == "__main__":
    main()
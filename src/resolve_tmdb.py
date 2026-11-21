import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from fetch_tmdb import (
    CACHE_DIR,
    FAILURES_PATH,
    REQUEST_DELAY,
    SELECTED_MOVIES_PATH,
    cache_is_valid,
    fetch_movie,
    save_to_cache,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESOLUTIONS_PATH = (
    PROJECT_ROOT / "data" / "staging" / "tmdb_id_resolutions.csv"
)

FIND_API_URL = "https://api.themoviedb.org/3/find"


def load_unresolved_movies():
    movies = pd.read_csv(
        SELECTED_MOVIES_PATH,
        dtype={
            "movieId": "int32",
            "imdbId": "string",
            "tmdbId": "Int64",
        },
    )

    failures = pd.read_csv(
        FAILURES_PATH,
        dtype={"tmdbId": "Int64"},
    )

    failed_ids = set(
        failures["tmdbId"].dropna().astype("int64")
    )

    unresolved = movies[
        movies["tmdbId"].isna()
        | movies["tmdbId"].isin(failed_ids)
    ].copy()

    return unresolved


def find_by_imdb(session, imdb_id):
    formatted_imdb_id = f"tt{imdb_id}"

    response = session.get(
        f"{FIND_API_URL}/{formatted_imdb_id}",
        params={
            "external_source": "imdb_id",
            "language": "en-US",
        },
        timeout=30,
    )

    response.raise_for_status()
    return response.json()


def classify_result(result):
    if result.get("movie_results"):
        return "movie", result["movie_results"][0]["id"]

    if result.get("tv_results"):
        return "tv", result["tv_results"][0]["id"]

    if result.get("tv_episode_results"):
        return "tv_episode", result["tv_episode_results"][0]["id"]

    return "no_match", None


def main():
    load_dotenv()
    token = os.getenv("TMDB_BEARER_TOKEN")

    if not token:
        raise RuntimeError(
            "TMDB_BEARER_TOKEN was not found in .env."
        )

    unresolved = load_unresolved_movies()
    resolutions = []

    print(f"Checking {len(unresolved)} unresolved movies.")

    with requests.Session() as session:
        session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "accept": "application/json",
            }
        )

        for _, row in unresolved.iterrows():
            movie_id = int(row["movieId"])
            title = row["title"]
            imdb_id = row["imdbId"]

            original_tmdb_id = (
                None
                if pd.isna(row["tmdbId"])
                else int(row["tmdbId"])
            )

            try:
                result = find_by_imdb(session, imdb_id)
                media_type, resolved_tmdb_id = classify_result(result)
                error = None

                if media_type == "movie":
                    cache_path = (
                        CACHE_DIR / f"{resolved_tmdb_id}.json"
                    )

                    if not cache_is_valid(
                        cache_path,
                        resolved_tmdb_id,
                    ):
                        movie_data, error = fetch_movie(
                            session,
                            resolved_tmdb_id,
                        )

                        if movie_data is not None:
                            save_to_cache(cache_path, movie_data)

                print(
                    f"{title}: {media_type}"
                    f" -> {resolved_tmdb_id}"
                )

            except requests.RequestException as request_error:
                media_type = "request_error"
                resolved_tmdb_id = None
                error = str(request_error)

                print(f"{title}: request failed")

            resolutions.append(
                {
                    "movieId": movie_id,
                    "title": title,
                    "imdbId": imdb_id,
                    "original_tmdbId": original_tmdb_id,
                    "resolved_tmdbId": resolved_tmdb_id,
                    "media_type": media_type,
                    "error": error,
                }
            )

            time.sleep(REQUEST_DELAY)

    pd.DataFrame(resolutions).to_csv(
        RESOLUTIONS_PATH,
        index=False,
    )

    print(f"\nSaved resolutions to: {RESOLUTIONS_PATH}")


if __name__ == "__main__":
    main()
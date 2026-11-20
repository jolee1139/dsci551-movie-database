from collections import Counter
from pathlib import Path
import json

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw" / "ml-20m"
STAGING_DIR = PROJECT_ROOT / "data" / "staging"

RATINGS_PATH = RAW_DATA_DIR / "ratings.csv"
MOVIES_PATH = RAW_DATA_DIR / "movies.csv"
LINKS_PATH = RAW_DATA_DIR / "links.csv"

OUTPUT_PATH = STAGING_DIR / "top_5000_movies.csv"
PROFILE_PATH = STAGING_DIR / "movielens_profile.json"

CHUNK_SIZE = 1_000_000
TOP_N = 5_000


def profile_ratings():
    rating_counts = pd.Series(dtype="int64")
    rating_sums = pd.Series(dtype="float64")
    user_ids = set()
    rating_distribution = Counter()

    total_ratings = 0
    earliest_timestamp = None
    latest_timestamp = None

    chunks = pd.read_csv(
        RATINGS_PATH,
        dtype={
            "userId": "int32",
            "movieId": "int32",
            "rating": "float32",
            "timestamp": "int64",
        },
        chunksize=CHUNK_SIZE,
    )

    for chunk_number, chunk in enumerate(chunks, start=1):
        total_ratings += len(chunk)
        user_ids.update(chunk["userId"].unique())

        grouped = chunk.groupby("movieId")["rating"].agg(["count", "sum"])

        rating_counts = rating_counts.add(grouped["count"], fill_value=0)
        rating_sums = rating_sums.add(grouped["sum"], fill_value=0)

        rating_distribution.update(chunk["rating"].value_counts().to_dict())

        chunk_min = int(chunk["timestamp"].min())
        chunk_max = int(chunk["timestamp"].max())

        earliest_timestamp = (
            chunk_min
            if earliest_timestamp is None
            else min(earliest_timestamp, chunk_min)
        )
        latest_timestamp = (
            chunk_max
            if latest_timestamp is None
            else max(latest_timestamp, chunk_max)
        )

        print(
            f"Processed chunk {chunk_number}: "
            f"{total_ratings:,} ratings total"
        )

    movie_statistics = pd.DataFrame(
        {
            "rating_count": rating_counts.astype("int64"),
            "rating_sum": rating_sums,
        }
    )

    movie_statistics.index.name = "movieId"
    movie_statistics = movie_statistics.reset_index()
    movie_statistics["movieId"] = movie_statistics["movieId"].astype("int32")

    movie_statistics["average_rating"] = (
        movie_statistics["rating_sum"]
        / movie_statistics["rating_count"]
    ).round(4)

    movie_statistics = movie_statistics.drop(columns="rating_sum")

    return {
        "movie_statistics": movie_statistics,
        "total_ratings": total_ratings,
        "unique_users": len(user_ids),
        "rating_distribution": rating_distribution,
        "earliest_timestamp": earliest_timestamp,
        "latest_timestamp": latest_timestamp,
    }


def select_top_movies(results):
    movies = pd.read_csv(
        MOVIES_PATH,
        dtype={
            "movieId": "int32",
            "title": "string",
            "genres": "string",
        },
    )

    links = pd.read_csv(
        LINKS_PATH,
        dtype={
            "movieId": "int32",
            "imdbId": "string",
            "tmdbId": "Int64",
        },
    )

    top_movies = (
        results["movie_statistics"]
        .sort_values(
            ["rating_count", "movieId"],
            ascending=[False, True],
        )
        .head(TOP_N)
        .merge(movies, on="movieId", how="left", validate="one_to_one")
        .merge(links, on="movieId", how="left", validate="one_to_one")
    )

    top_movies = top_movies[
        [
            "movieId",
            "title",
            "genres",
            "imdbId",
            "tmdbId",
            "rating_count",
            "average_rating",
        ]
    ]

    return top_movies, movies, links


def save_results(results, top_movies, movies, links):
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    top_movies.to_csv(OUTPUT_PATH, index=False)

    rating_distribution = {
        str(rating): int(results["rating_distribution"][rating])
        for rating in sorted(results["rating_distribution"])
    }

    profile = {
        "total_ratings": results["total_ratings"],
        "unique_users": results["unique_users"],
        "rated_movies": len(results["movie_statistics"]),
        "catalog_movies": len(movies),
        "link_records": len(links),
        "earliest_rating_utc": pd.to_datetime(
            results["earliest_timestamp"], unit="s", utc=True
        ).isoformat(),
        "latest_rating_utc": pd.to_datetime(
            results["latest_timestamp"], unit="s", utc=True
        ).isoformat(),
        "rating_distribution": rating_distribution,
        "selected_movies": len(top_movies),
        "selected_with_tmdb_id": int(top_movies["tmdbId"].notna().sum()),
        "selected_without_tmdb_id": int(top_movies["tmdbId"].isna().sum()),
    }

    PROFILE_PATH.write_text(
        json.dumps(profile, indent=2),
        encoding="utf-8",
    )

    print(f"\nSaved selected movies to: {OUTPUT_PATH}")
    print(f"Saved profile to: {PROFILE_PATH}")
    print("\nTop 10 most-rated movies:")
    print(
        top_movies[["title", "rating_count"]]
        .head(10)
        .to_string(index=False)
    )


def main():
    results = profile_ratings()
    top_movies, movies, links = select_top_movies(results)
    save_results(results, top_movies, movies, links)


if __name__ == "__main__":
    main()
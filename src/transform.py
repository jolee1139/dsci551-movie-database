import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "ml-20m"
STAGING_DIR = PROJECT_ROOT / "data" / "staging"
CACHE_DIR = PROJECT_ROOT / "data" / "tmdb_cache"
LOAD_DIR = STAGING_DIR / "load"

RAW_MOVIES_PATH = RAW_DIR / "movies.csv"
RAW_RATINGS_PATH = RAW_DIR / "ratings.csv"

SELECTED_PATH = STAGING_DIR / "top_5000_movies.csv"
RESOLUTIONS_PATH = STAGING_DIR / "tmdb_id_resolutions.csv"

MOVIES_OUTPUT = LOAD_DIR / "movies.csv"
USERS_OUTPUT = LOAD_DIR / "users.csv"
RATINGS_OUTPUT = LOAD_DIR / "ratings.csv"
GENRES_OUTPUT = LOAD_DIR / "genres.csv"
MOVIE_GENRES_OUTPUT = LOAD_DIR / "movie_genres.csv"
MOVIE_DETAILS_OUTPUT = LOAD_DIR / "movie_details.csv"
SUMMARY_OUTPUT = LOAD_DIR / "transform_summary.json"

CHUNK_SIZE = 1_000_000


def clean_text(value):
    if value is None:
        return None

    cleaned = " ".join(str(value).split())
    return cleaned if cleaned else None


def positive_integer(value):
    if value is None:
        return None

    number = int(value)
    return number if number > 0 else None


def transform_movie_details():
    records = []

    cache_paths = sorted(
        CACHE_DIR.glob("*.json"),
        key=lambda path: int(path.stem),
    )

    for cache_path in cache_paths:
        try:
            data = json.loads(
                cache_path.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError) as error:
            raise ValueError(
                f"Invalid cache file: {cache_path}"
            ) from error

        tmdb_id = int(data["id"])

        if tmdb_id != int(cache_path.stem):
            raise ValueError(
                f"TMDB ID mismatch in {cache_path}"
            )

        records.append(
            {
                "tmdb_id": tmdb_id,
                "imdb_id": data.get("imdb_id"),
                "tmdb_title": clean_text(data.get("title")),
                "original_title": clean_text(
                    data.get("original_title")
                ),
                "overview": clean_text(data.get("overview")),
                "release_date": data.get("release_date") or None,
                "runtime_minutes": positive_integer(
                    data.get("runtime")
                ),
                "budget": positive_integer(data.get("budget")),
                "revenue": positive_integer(data.get("revenue")),
                "original_language": data.get(
                    "original_language"
                ),
                "popularity": data.get("popularity"),
                "vote_average": data.get("vote_average"),
                "vote_count": data.get("vote_count"),
                "status": clean_text(data.get("status")),
                "tagline": clean_text(data.get("tagline")),
                "poster_path": data.get("poster_path"),
            }
        )

    details = pd.DataFrame(records)

    if details["tmdb_id"].duplicated().any():
        raise ValueError(
            "Duplicate TMDB IDs found in movie details."
        )

    return details.sort_values("tmdb_id")


def build_verified_tmdb_mapping(valid_tmdb_ids):
    selected = pd.read_csv(
        SELECTED_PATH,
        dtype={
            "movieId": "int32",
            "imdbId": "string",
            "tmdbId": "Int64",
        },
    )

    resolutions = pd.read_csv(
        RESOLUTIONS_PATH,
        dtype={
            "movieId": "int32",
            "resolved_tmdbId": "Int64",
            "media_type": "string",
        },
    )

    movie_resolutions = resolutions[
        (resolutions["media_type"] == "movie")
        & resolutions["resolved_tmdbId"].notna()
    ]

    correction_map = {
        int(row.movieId): int(row.resolved_tmdbId)
        for row in movie_resolutions.itertuples()
    }

    verified_mapping = {}

    for row in selected.itertuples():
        movie_id = int(row.movieId)

        if movie_id in correction_map:
            candidate_tmdb_id = correction_map[movie_id]
        elif pd.notna(row.tmdbId):
            candidate_tmdb_id = int(row.tmdbId)
        else:
            candidate_tmdb_id = None

        if candidate_tmdb_id in valid_tmdb_ids:
            verified_mapping[movie_id] = candidate_tmdb_id

    return selected, resolutions, verified_mapping


def transform_movies_and_genres(tmdb_mapping):
    source_movies = pd.read_csv(
        RAW_MOVIES_PATH,
        dtype={
            "movieId": "int32",
            "title": "string",
            "genres": "string",
        },
    )

    release_year = source_movies["title"].str.extract(
        r"\((\d{4})\)\s*$",
        expand=False,
    ).astype("Int64")

    clean_titles = (
        source_movies["title"]
        .str.replace(
            r"\s*\(\d{4}\)\s*$",
            "",
            regex=True,
        )
        .str.strip()
    )

    movies = pd.DataFrame(
        {
            "movie_id": source_movies["movieId"],
            "title": clean_titles,
            "release_year": release_year,
        }
    )

    movies["tmdb_id"] = (
        movies["movie_id"]
        .map(tmdb_mapping)
        .astype("Int64")
    )

    genre_rows = (
        source_movies[["movieId", "genres"]]
        .assign(
            genre_name=source_movies["genres"]
            .fillna("")
            .str.split("|")
        )
        .explode("genre_name")
    )

    genre_rows["genre_name"] = (
        genre_rows["genre_name"].str.strip()
    )

    genre_rows = genre_rows[
        (genre_rows["genre_name"] != "")
        & (
            genre_rows["genre_name"]
            != "(no genres listed)"
        )
    ]

    genre_names = sorted(
        genre_rows["genre_name"].unique()
    )

    genres = pd.DataFrame(
        {
            "genre_id": range(1, len(genre_names) + 1),
            "genre_name": genre_names,
        }
    )

    genre_lookup = dict(
        zip(genres["genre_name"], genres["genre_id"])
    )

    movie_genres = pd.DataFrame(
        {
            "movie_id": genre_rows["movieId"],
            "genre_id": genre_rows["genre_name"].map(
                genre_lookup
            ),
        }
    )

    movie_genres = (
        movie_genres
        .drop_duplicates()
        .sort_values(["movie_id", "genre_id"])
    )

    return source_movies, movies, genres, movie_genres


def transform_ratings(valid_movie_ids):
    user_ids = set()
    total_ratings = 0
    first_chunk = True

    chunks = pd.read_csv(
        RAW_RATINGS_PATH,
        dtype={
            "userId": "int32",
            "movieId": "int32",
            "rating": "float32",
            "timestamp": "int64",
        },
        chunksize=CHUNK_SIZE,
    )

    for chunk_number, chunk in enumerate(chunks, start=1):
        unknown_movie_ids = (
            set(chunk["movieId"].unique())
            - valid_movie_ids
        )

        if unknown_movie_ids:
            raise ValueError(
                "Ratings contain unknown movie IDs: "
                f"{sorted(unknown_movie_ids)[:10]}"
            )

        if not chunk["rating"].between(0.5, 5.0).all():
            raise ValueError(
                f"Invalid rating found in chunk {chunk_number}."
            )

        user_ids.update(chunk["userId"].unique())

        transformed = pd.DataFrame(
            {
                "user_id": chunk["userId"],
                "movie_id": chunk["movieId"],
                "rating": chunk["rating"],
                "rated_at": pd.to_datetime(
                    chunk["timestamp"],
                    unit="s",
                    utc=True,
                ).dt.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

        transformed.to_csv(
            RATINGS_OUTPUT,
            mode="w" if first_chunk else "a",
            header=first_chunk,
            index=False,
        )

        first_chunk = False
        total_ratings += len(chunk)

        print(
            f"Transformed ratings chunk {chunk_number}: "
            f"{total_ratings:,} rows"
        )

    users = pd.DataFrame(
        {"user_id": sorted(int(value) for value in user_ids)}
    )

    return users, total_ratings


def validate_relationships(
    movies,
    movie_details,
    genres,
    movie_genres,
):
    if movies["movie_id"].duplicated().any():
        raise ValueError("Duplicate movie IDs found.")

    valid_tmdb_ids = set(movie_details["tmdb_id"])
    referenced_tmdb_ids = set(
        movies["tmdb_id"].dropna().astype("int64")
    )

    if not referenced_tmdb_ids.issubset(valid_tmdb_ids):
        raise ValueError(
            "A movie references a missing TMDB detail record."
        )

    valid_movie_ids = set(movies["movie_id"])
    valid_genre_ids = set(genres["genre_id"])

    if not set(movie_genres["movie_id"]).issubset(
        valid_movie_ids
    ):
        raise ValueError(
            "movie_genres contains an invalid movie ID."
        )

    if not set(movie_genres["genre_id"]).issubset(
        valid_genre_ids
    ):
        raise ValueError(
            "movie_genres contains an invalid genre ID."
        )


def main():
    LOAD_DIR.mkdir(parents=True, exist_ok=True)

    print("Transforming cached TMDB movie details...")
    movie_details = transform_movie_details()

    valid_tmdb_ids = set(movie_details["tmdb_id"])

    selected, resolutions, tmdb_mapping = (
        build_verified_tmdb_mapping(valid_tmdb_ids)
    )

    print("Transforming movies and genres...")
    (
        source_movies,
        movies,
        genres,
        movie_genres,
    ) = transform_movies_and_genres(tmdb_mapping)

    validate_relationships(
        movies,
        movie_details,
        genres,
        movie_genres,
    )

    print("Transforming ratings and users...")
    users, total_ratings = transform_ratings(
        set(source_movies["movieId"])
    )

    movies.to_csv(MOVIES_OUTPUT, index=False)
    users.to_csv(USERS_OUTPUT, index=False)
    genres.to_csv(GENRES_OUTPUT, index=False)
    movie_genres.to_csv(
        MOVIE_GENRES_OUTPUT,
        index=False,
    )
    movie_details.to_csv(
        MOVIE_DETAILS_OUTPUT,
        index=False,
    )

    resolution_counts = {
        str(name): int(count)
        for name, count in (
            resolutions["media_type"]
            .value_counts(dropna=False)
            .items()
        )
    }

    summary = {
        "movies": len(movies),
        "movies_with_tmdb_details": int(
            movies["tmdb_id"].notna().sum()
        ),
        "movies_without_tmdb_details": int(
            movies["tmdb_id"].isna().sum()
        ),
        "selected_movies": len(selected),
        "selected_without_tmdb_details": (
            len(selected) - len(tmdb_mapping)
        ),
        "movie_details": len(movie_details),
        "users": len(users),
        "ratings": total_ratings,
        "genres": len(genres),
        "movie_genres": len(movie_genres),
        "resolution_results": resolution_counts,
    }

    SUMMARY_OUTPUT.write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\nTransformation complete.")
    print(json.dumps(summary, indent=2))
    print(f"\nLoad-ready files saved to: {LOAD_DIR}")


if __name__ == "__main__":
    main()
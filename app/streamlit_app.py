import os
from pathlib import Path

import mysql.connector
import pandas as pd
import streamlit as st
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


st.set_page_config(
    page_title="Movie Database Explorer",
    page_icon="🎬",
    layout="wide",
)


def database_config():
    config = {
        "host": os.getenv("MYSQL_HOST"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "database": os.getenv("MYSQL_DATABASE"),
        "user": os.getenv("MYSQL_USER"),
        "password": os.getenv("MYSQL_PASSWORD"),
    }

    missing = [
        name
        for name, value in config.items()
        if value in (None, "")
    ]

    if missing:
        raise RuntimeError(
            "Missing database configuration: "
            + ", ".join(missing)
        )

    return config


def query_dataframe(query, parameters=None):
    connection = mysql.connector.connect(
        **database_config()
    )

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, parameters or ())
        rows = cursor.fetchall()
        columns = cursor.column_names
        cursor.close()

        return pd.DataFrame(rows, columns=columns)
    finally:
        connection.close()


@st.cache_data(
    ttl=600,
    show_spinner="Loading the movie catalog...",
)
def load_catalog():
    query = """
        WITH rating_stats AS (
            SELECT
                movie_id,
                COUNT(*) AS rating_count,
                AVG(rating) AS average_rating
            FROM ratings
            GROUP BY movie_id
        ),
        genre_lists AS (
            SELECT
                mg.movie_id,
                GROUP_CONCAT(
                    g.genre_name
                    ORDER BY g.genre_name
                    SEPARATOR ', '
                ) AS genres
            FROM movie_genres AS mg
            JOIN genres AS g
                ON g.genre_id = mg.genre_id
            GROUP BY mg.movie_id
        )
        SELECT
            m.movie_id,
            m.title,
            m.release_year,
            m.tmdb_id,
            COALESCE(rs.rating_count, 0) AS rating_count,
            ROUND(rs.average_rating, 2) AS average_rating,
            COALESCE(gl.genres, '') AS genres
        FROM movies AS m
        LEFT JOIN rating_stats AS rs
            ON rs.movie_id = m.movie_id
        LEFT JOIN genre_lists AS gl
            ON gl.movie_id = m.movie_id
        ORDER BY
            rating_count DESC,
            m.movie_id;
    """

    catalog = query_dataframe(query)

    catalog["movie_id"] = pd.to_numeric(
        catalog["movie_id"]
    )
    catalog["release_year"] = pd.to_numeric(
        catalog["release_year"],
        errors="coerce",
    )
    catalog["tmdb_id"] = pd.to_numeric(
        catalog["tmdb_id"],
        errors="coerce",
    )
    catalog["rating_count"] = pd.to_numeric(
        catalog["rating_count"]
    ).fillna(0).astype(int)
    catalog["average_rating"] = pd.to_numeric(
        catalog["average_rating"],
        errors="coerce",
    )
    catalog["genres"] = catalog["genres"].fillna("")

    return catalog


@st.cache_data(ttl=600, show_spinner=False)
def load_user_count():
    result = query_dataframe(
        "SELECT COUNT(*) AS user_count FROM users;"
    )
    return int(result.iloc[0]["user_count"])


@st.cache_data(ttl=600, show_spinner=False)
def load_movie_details(movie_id):
    query = """
        SELECT
            m.movie_id,
            m.title,
            m.release_year,
            m.tmdb_id,
            md.imdb_id,
            md.tmdb_title,
            md.original_title,
            md.overview,
            md.release_date,
            md.runtime_minutes,
            md.budget,
            md.revenue,
            md.original_language,
            md.popularity,
            md.vote_average,
            md.vote_count,
            md.status,
            md.tagline
        FROM movies AS m
        LEFT JOIN movie_details AS md
            ON md.tmdb_id = m.tmdb_id
        WHERE m.movie_id = %s;
    """

    return query_dataframe(query, (int(movie_id),))


@st.cache_data(ttl=600, show_spinner=False)
def load_rating_distribution(movie_id):
    query = """
        SELECT
            rating,
            COUNT(*) AS rating_count
        FROM ratings
        WHERE movie_id = %s
        GROUP BY rating
        ORDER BY rating;
    """

    distribution = query_dataframe(
        query,
        (int(movie_id),),
    )

    distribution["rating"] = pd.to_numeric(
        distribution["rating"]
    )
    distribution["rating_count"] = pd.to_numeric(
        distribution["rating_count"]
    )

    return distribution


def format_currency(value):
    if value is None or pd.isna(value):
        return "Unknown"

    return f"${int(value):,}"


st.title("🎬 Movie Database Explorer")

st.write(
    "Explore MovieLens ratings joined with movie metadata "
    "from TMDB."
)

try:
    catalog = load_catalog()
    user_count = load_user_count()
except (mysql.connector.Error, RuntimeError) as error:
    st.error(f"Database connection failed: {error}")
    st.info(
        "Confirm that MySQL is running and that the values "
        "in your private .env file are correct."
    )
    st.stop()


total_ratings = int(catalog["rating_count"].sum())
enriched_movies = int(catalog["tmdb_id"].notna().sum())

metric_columns = st.columns(4)

metric_columns[0].metric(
    "Movies",
    f"{len(catalog):,}",
)
metric_columns[1].metric(
    "Ratings",
    f"{total_ratings:,}",
)
metric_columns[2].metric(
    "Users",
    f"{user_count:,}",
)
metric_columns[3].metric(
    "TMDB-enriched movies",
    f"{enriched_movies:,}",
)


st.sidebar.header("Movie filters")

title_search = st.sidebar.text_input(
    "Title contains",
    placeholder="Example: Toy Story",
)

genre_options = sorted(
    {
        genre
        for value in catalog["genres"]
        if value
        for genre in value.split(", ")
    }
)

selected_genres = st.sidebar.multiselect(
    "Genres",
    genre_options,
)

valid_years = catalog["release_year"].dropna()

minimum_year = int(valid_years.min())
maximum_year = int(valid_years.max())

year_range = st.sidebar.slider(
    "Release year",
    min_value=minimum_year,
    max_value=maximum_year,
    value=(minimum_year, maximum_year),
)

minimum_ratings = st.sidebar.number_input(
    "Minimum number of ratings",
    min_value=0,
    max_value=int(catalog["rating_count"].max()),
    value=100,
    step=100,
)

sort_choice = st.sidebar.selectbox(
    "Sort results by",
    [
        "Most rated",
        "Highest rated",
        "Newest",
        "Title",
    ],
)

result_limit = st.sidebar.slider(
    "Movies to display",
    min_value=10,
    max_value=200,
    value=50,
    step=10,
)


filtered = catalog.copy()

if title_search:
    filtered = filtered[
        filtered["title"].str.contains(
            title_search,
            case=False,
            regex=False,
            na=False,
        )
    ]

if selected_genres:
    filtered = filtered[
        filtered["genres"].apply(
            lambda value: any(
                genre in value.split(", ")
                for genre in selected_genres
            )
        )
    ]

filtered = filtered[
    filtered["release_year"]
    .between(year_range[0], year_range[1])
    .fillna(False)
]

filtered = filtered[
    filtered["rating_count"] >= minimum_ratings
]

if sort_choice == "Most rated":
    filtered = filtered.sort_values(
        ["rating_count", "average_rating"],
        ascending=[False, False],
    )
elif sort_choice == "Highest rated":
    filtered = filtered.sort_values(
        ["average_rating", "rating_count"],
        ascending=[False, False],
        na_position="last",
    )
elif sort_choice == "Newest":
    filtered = filtered.sort_values(
        ["release_year", "rating_count"],
        ascending=[False, False],
        na_position="last",
    )
else:
    filtered = filtered.sort_values(
        ["title", "release_year"]
    )

displayed = filtered.head(result_limit).copy()


explore_tab, genre_tab, project_tab = st.tabs(
    [
        "Explore movies",
        "Genre insights",
        "Project summary",
    ]
)


with explore_tab:
    st.subheader(
        f"Movie results ({len(filtered):,} matches)"
    )

    if displayed.empty:
        st.warning(
            "No movies match the selected filters."
        )
    else:
        result_table = displayed[
            [
                "title",
                "release_year",
                "genres",
                "rating_count",
                "average_rating",
            ]
        ].rename(
            columns={
                "title": "Title",
                "release_year": "Release year",
                "genres": "Genres",
                "rating_count": "Rating count",
                "average_rating": "Average rating",
            }
        )

        st.dataframe(
            result_table,
            hide_index=True,
            width="stretch",
            column_config={
                "Average rating": (
                    st.column_config.NumberColumn(
                        format="%.2f"
                    )
                ),
                "Rating count": (
                    st.column_config.NumberColumn(
                        format="%d"
                    )
                ),
            },
        )

        label_lookup = {}

        for row in displayed.itertuples():
            year = (
                str(int(row.release_year))
                if pd.notna(row.release_year)
                else "Year unknown"
            )

            label_lookup[int(row.movie_id)] = (
                f"{row.title} ({year})"
            )

        selected_movie_id = st.selectbox(
            "Select a movie for details",
            options=list(label_lookup),
            format_func=label_lookup.get,
        )

        selected_catalog_row = catalog[
            catalog["movie_id"] == selected_movie_id
        ].iloc[0]

        details = load_movie_details(
            selected_movie_id
        ).iloc[0]

        st.divider()

        detail_year = (
            str(int(details["release_year"]))
            if pd.notna(details["release_year"])
            else "Year unknown"
        )

        st.subheader(
            f"{details['title']} ({detail_year})"
        )

        st.caption(
            selected_catalog_row["genres"]
            or "No genres listed"
        )

        detail_metrics = st.columns(4)

        detail_metrics[0].metric(
            "MovieLens rating",
            (
                f"{selected_catalog_row['average_rating']:.2f}/5"
                if pd.notna(
                    selected_catalog_row[
                        "average_rating"
                    ]
                )
                else "N/A"
            ),
        )

        detail_metrics[1].metric(
            "Rating count",
            f"{selected_catalog_row['rating_count']:,}",
        )

        detail_metrics[2].metric(
            "Runtime",
            (
                f"{int(details['runtime_minutes'])} min"
                if pd.notna(
                    details["runtime_minutes"]
                )
                else "Unknown"
            ),
        )

        detail_metrics[3].metric(
            "TMDB rating",
            (
                f"{float(details['vote_average']):.2f}/10"
                if pd.notna(
                    details["vote_average"]
                )
                else "N/A"
            ),
        )

        if pd.notna(details["tagline"]):
            st.markdown(f"*{details['tagline']}*")

        st.write(
            details["overview"]
            if pd.notna(details["overview"])
            else "No TMDB overview is available."
        )

        info_columns = st.columns(3)

        info_columns[0].write(
            "**Release date:** "
            + (
                str(details["release_date"])
                if pd.notna(
                    details["release_date"]
                )
                else "Unknown"
            )
        )

        info_columns[1].write(
            "**Budget:** "
            + format_currency(details["budget"])
        )

        info_columns[2].write(
            "**Revenue:** "
            + format_currency(details["revenue"])
        )

        distribution = load_rating_distribution(
            selected_movie_id
        )

        st.subheader("MovieLens rating distribution")

        st.bar_chart(
            distribution,
            x="rating",
            y="rating_count",
        )


with genre_tab:
    st.subheader("Genre-level rating analysis")

    genre_rows = catalog[
        catalog["genres"] != ""
    ].copy()

    genre_rows["genre_name"] = (
        genre_rows["genres"].str.split(", ")
    )

    genre_rows = genre_rows.explode("genre_name")

    genre_rows["weighted_rating_sum"] = (
        genre_rows["average_rating"]
        * genre_rows["rating_count"]
    )

    genre_summary = (
        genre_rows.groupby(
            "genre_name",
            as_index=False,
        )
        .agg(
            movie_count=("movie_id", "nunique"),
            rating_count=("rating_count", "sum"),
            weighted_rating_sum=(
                "weighted_rating_sum",
                "sum",
            ),
        )
    )

    genre_summary = genre_summary[
        genre_summary["rating_count"] > 0
    ]

    genre_summary["average_rating"] = (
        genre_summary["weighted_rating_sum"]
        / genre_summary["rating_count"]
    )

    genre_summary = genre_summary.sort_values(
        "average_rating",
        ascending=False,
    )

    chart_columns = st.columns(2)

    with chart_columns[0]:
        st.write("**Average rating by genre**")
        st.bar_chart(
            genre_summary,
            x="genre_name",
            y="average_rating",
        )

    with chart_columns[1]:
        st.write("**Total ratings by genre**")
        st.bar_chart(
            genre_summary,
            x="genre_name",
            y="rating_count",
        )

    genre_table = genre_summary[
        [
            "genre_name",
            "movie_count",
            "rating_count",
            "average_rating",
        ]
    ].rename(
        columns={
            "genre_name": "Genre",
            "movie_count": "Movies",
            "rating_count": "Ratings",
            "average_rating": "Average rating",
        }
    )

    st.dataframe(
        genre_table,
        hide_index=True,
        width="stretch",
        column_config={
            "Average rating": (
                st.column_config.NumberColumn(
                    format="%.2f"
                )
            )
        },
    )


with project_tab:
    st.subheader("Project data pipeline")

    st.markdown(
        """
        1. Downloaded and profiled MovieLens 20M.
        2. Selected the 5,000 most-rated movies.
        3. Fetched and cached TMDB movie details.
        4. Resolved missing identifiers using IMDb IDs.
        5. Transformed the data into normalized tables.
        6. Loaded the tables into MySQL.
        7. Added a covering index for analytical queries.
        """
    )

    st.subheader("Index experiment")

    index_columns = st.columns(3)

    index_columns[0].metric(
        "Baseline median",
        "184.311 sec",
    )
    index_columns[1].metric(
        "Covering-index median",
        "4.137 sec",
    )
    index_columns[2].metric(
        "Median speedup",
        "44.6×",
    )

    st.subheader("Data limitations")

    st.markdown(
        """
        - MovieLens ratings cover activity through March 2015.
        - TMDB metadata reflects the time it was fetched.
        - MovieLens includes some television and miniseries entries.
        - Only records classified as movies by TMDB were enriched.
        - Seventeen selected MovieLens records lack verified TMDB
          movie details.
        """
    )


st.divider()

st.caption(
    "This product uses the TMDB API but is not endorsed "
    "or certified by TMDB."
)
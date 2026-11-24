# MovieLens + TMDB Movie Database

A relational movie database built with MovieLens 20M, TMDB metadata,
MySQL, Python, and Streamlit.

The project processes more than 20 million ratings, enriches the 5,000
most-rated MovieLens entries with verified TMDB movie metadata, loads
the normalized data into MySQL, and provides an interactive dashboard
for exploring movies and rating patterns.

## Project Results

| Table             |    Records |
| ----------------- | ---------: |
| `movies`        |     27,278 |
| `users`         |    138,493 |
| `ratings`       | 20,000,263 |
| `movie_details` |      4,983 |
| `genres`        |         19 |
| `movie_genres`  |     54,160 |

Of the 5,000 movies selected for enrichment:

- 4,983 received verified TMDB movie details.
- 15 were classified by TMDB as television or miniseries records.
- 2 could not be matched confidently.
- Unverified records remain in `movies` with a nullable `tmdb_id`.

## Features

- Reproducible MovieLens 20M download
- Chunked processing of 20 million ratings
- Selection of the 5,000 most-rated movies
- TMDB API enrichment with local JSON caching
- Resume support and API retry handling
- IMDb-based fallback matching
- Normalized MySQL schema with foreign keys
- Bulk CSV loading with `LOAD DATA LOCAL INFILE`
- Analytical SQL queries
- Query-plan and covering-index experiment
- Interactive Streamlit dashboard
- Title, genre, year, rating-count, and sorting filters
- Movie details and rating-distribution visualizations
- Genre-level insights

## Data Sources

### MovieLens 20M

MovieLens 20M contains 20,000,263 ratings from 138,493 users across
27,278 movies.

Source: [GroupLens MovieLens 20M](https://grouplens.org/datasets/movielens/20m/)

### TMDB

TMDB provides supplemental movie metadata such as runtime, overview,
release date, budget, revenue, language, popularity, and vote totals.

Source: [The Movie Database API](https://developer.themoviedb.org/docs/getting-started)

This product uses the TMDB API but is not endorsed or certified by TMDB.

## Database Schema

The database contains six tables:

- `users` — anonymous MovieLens user identifiers
- `movies` — MovieLens movies and optional verified TMDB identifiers
- `ratings` — user ratings and rating timestamps
- `genres` — normalized genre names
- `movie_genres` — many-to-many movie–genre relationships
- `movie_details` — verified TMDB metadata

`movies.tmdb_id` is a nullable, non-unique foreign key referencing
`movie_details.tmdb_id`. This permits multiple MovieLens records to
reference one TMDB record while retaining movies that could not be
enriched.

## Repository Structure

```text
dsci551-movie-database/
├── app/
│   └── streamlit_app.py
├── data/
│   ├── raw/
│   ├── staging/
│   └── tmdb_cache/
├── experiments/
│   ├── 01_index_benchmark.sql
│   ├── baseline_plan.txt
│   ├── covering_plan.txt
│   ├── repeated_plans.txt
│   └── README.md
├── sql/
│   ├── 01_schema.sql
│   ├── 02_load.sql
│   └── 03_queries.sql
├── src/
│   ├── download_movielens.py
│   ├── profile_and_select.py
│   ├── fetch_tmdb.py
│   ├── resolve_tmdb.py
│   └── transform.py
├── .streamlit/
│   └── config.toml
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

Generated data, API responses, virtual environments, and private
credentials are excluded from Git.

## Prerequisites

- Python 3.10 or newer
- MySQL 8.4 or newer
- A TMDB account and API Read Access Token
- Approximately 3 GB of available local storage

## Installation

Clone the repository and enter it:

```bash
git clone https://github.com/jolee1139/dsci551-movie-database.git
cd dsci551-movie-database
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the Python dependencies:

```bash
python -m pip install -r requirements.txt
```

## Environment Configuration

Copy the safe environment template:

```bash
cp .env.example .env
```

Fill in the private values inside `.env`:

```text
TMDB_BEARER_TOKEN=your_tmdb_read_access_token
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=movie_database
MYSQL_USER=movie_app
MYSQL_PASSWORD=your_private_database_password
```

Never commit `.env`. It is excluded by `.gitignore`.

## Data Pipeline

Run every command from the repository root.

### 1. Download MovieLens 20M

```bash
python src/download_movielens.py
```

### 2. Profile the ratings and select 5,000 movies

```bash
python src/profile_and_select.py
```

This creates:

```text
data/staging/top_5000_movies.csv
data/staging/movielens_profile.json
```

### 3. Test TMDB access and caching

```bash
python src/fetch_tmdb.py --limit 3
```

Run it again to confirm the three responses are detected as cached.

### 4. Fetch all available TMDB movie details

```bash
python src/fetch_tmdb.py
```

The script can be stopped and restarted. Existing valid cache files
are skipped automatically.

### 5. Resolve failed and missing identifiers

```bash
python src/resolve_tmdb.py
```

The resolver uses IMDb IDs to identify current TMDB movie, television,
or unmatched records.

### 6. Create database-ready files

```bash
python src/transform.py
```

The load-ready CSV files are written to:

```text
data/staging/load/
```

## MySQL Setup

Create the database and project account as a MySQL administrator:

```sql
CREATE DATABASE movie_database
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

CREATE USER 'movie_app'@'localhost'
IDENTIFIED BY 'your_private_database_password';

GRANT ALL PRIVILEGES ON movie_database.*
TO 'movie_app'@'localhost';
```

Enable local loading as an administrator:

```sql
SET PERSIST local_infile = ON;
```

Create the tables:

```bash
mysql -u movie_app -p movie_database < sql/01_schema.sql
```

Load the generated CSV files:

```bash
mysql --local-infile=1 -u movie_app -p movie_database < sql/02_load.sql
```

These commands must be executed from the repository root because
`02_load.sql` uses repository-relative file paths.

Warning: `01_schema.sql` drops and recreates the tables, and
`02_load.sql` truncates them before loading.

## Analytical Queries

Run the analytical query suite:

```bash
mysql -u movie_app -p --table movie_database < sql/03_queries.sql
```

The queries analyze:

- Most-rated movies
- Highest-rated popular movies
- Genre performance
- Ratings by release decade
- MovieLens and TMDB rating disagreement
- Financial return
- Most active users

## Index Performance Experiment

The experiment compared:

```sql
INDEX idx_ratings_movie_id (movie_id)
```

with the covering index:

```sql
INDEX idx_ratings_movie_rating (movie_id, rating)
```

Test query:

```sql
SELECT
    movie_id,
    COUNT(*) AS rating_count,
    AVG(rating) AS average_rating
FROM ratings
GROUP BY movie_id;
```

### Results

|            Trial |       Baseline index |     Covering index |
| ---------------: | -------------------: | -----------------: |
|                1 |           178,584 ms |           4,065 ms |
|                2 |           193,989 ms |           3,916 ms |
|                3 |           197,579 ms |           3,953 ms |
| **Median** | **193,989 ms** | **3,953 ms** |

The covering index reduced median execution time by approximately
98.0% and produced a 49.1× speedup.

Detailed methodology and execution plans are available in
[`experiments/README.md`](experiments/README.md).

## Streamlit Dashboard

Start the application:

```bash
python -m streamlit run app/streamlit_app.py
```

Then open:

```text
http://localhost:8501
```

The dashboard includes:

- Database summary metrics
- Search and filter controls
- Sortable movie results
- Detailed movie metadata
- MovieLens rating distributions
- Genre-level charts
- Project methodology and index results

## Limitations

- MovieLens 20M ratings end in March 2015.
- TMDB metadata reflects the date it was fetched.
- TMDB metadata can change over time.
- MovieLens includes some television and miniseries entries.
- Only records classified as movies by TMDB were enriched.
- Seventeen selected records lack verified TMDB movie details.
- Generated datasets and cached API responses are intentionally not
  stored in Git.

## Security

- `.env` contains private credentials and must remain local.
- `.env.example` documents required variables without real secrets.
- The application connects with the limited `movie_app` account rather
  than the administrative MySQL `root` account.
- `LOAD DATA LOCAL` should be used only with a trusted local MySQL
  server and trusted project files.

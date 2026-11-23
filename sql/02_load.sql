USE movie_database;

SET FOREIGN_KEY_CHECKS = 0;
SET UNIQUE_CHECKS = 0;

TRUNCATE TABLE movie_genres;
TRUNCATE TABLE ratings;
TRUNCATE TABLE genres;
TRUNCATE TABLE movies;
TRUNCATE TABLE users;
TRUNCATE TABLE movie_details;


SELECT 'Loading movie_details...' AS status;

LOAD DATA LOCAL INFILE
'/Users/yoey_danjuma/Desktop/DSCI551/dsci551-movie-database/data/staging/load/movie_details.csv'
INTO TABLE movie_details
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
ESCAPED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(
    @tmdb_id,
    @imdb_id,
    @tmdb_title,
    @original_title,
    @overview,
    @release_date,
    @runtime_minutes,
    @budget,
    @revenue,
    @original_language,
    @popularity,
    @vote_average,
    @vote_count,
    @status,
    @tagline,
    @poster_path
)
SET
    tmdb_id = @tmdb_id,
    imdb_id = NULLIF(@imdb_id, ''),
    tmdb_title = @tmdb_title,
    original_title = NULLIF(@original_title, ''),
    overview = NULLIF(@overview, ''),
    release_date = NULLIF(@release_date, ''),
    runtime_minutes = NULLIF(@runtime_minutes, ''),
    budget = NULLIF(@budget, ''),
    revenue = NULLIF(@revenue, ''),
    original_language = NULLIF(@original_language, ''),
    popularity = NULLIF(@popularity, ''),
    vote_average = NULLIF(@vote_average, ''),
    vote_count = NULLIF(@vote_count, ''),
    status = NULLIF(@status, ''),
    tagline = NULLIF(@tagline, ''),
    poster_path = NULLIF(@poster_path, '');

SELECT ROW_COUNT() AS movie_details_loaded;


SELECT 'Loading users...' AS status;

LOAD DATA LOCAL INFILE
'/Users/yoey_danjuma/Desktop/DSCI551/dsci551-movie-database/data/staging/load/users.csv'
INTO TABLE users
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
ESCAPED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(user_id);

SELECT ROW_COUNT() AS users_loaded;


SELECT 'Loading movies...' AS status;

LOAD DATA LOCAL INFILE
'/Users/yoey_danjuma/Desktop/DSCI551/dsci551-movie-database/data/staging/load/movies.csv'
INTO TABLE movies
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
ESCAPED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(
    @movie_id,
    @title,
    @release_year,
    @tmdb_id
)
SET
    movie_id = @movie_id,
    title = @title,
    release_year = NULLIF(@release_year, ''),
    tmdb_id = NULLIF(@tmdb_id, '');

SELECT ROW_COUNT() AS movies_loaded;


SELECT 'Loading genres...' AS status;

LOAD DATA LOCAL INFILE
'/Users/yoey_danjuma/Desktop/DSCI551/dsci551-movie-database/data/staging/load/genres.csv'
INTO TABLE genres
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
ESCAPED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(genre_id, genre_name);

SELECT ROW_COUNT() AS genres_loaded;


SELECT 'Loading movie_genres...' AS status;

LOAD DATA LOCAL INFILE
'/Users/yoey_danjuma/Desktop/DSCI551/dsci551-movie-database/data/staging/load/movie_genres.csv'
INTO TABLE movie_genres
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
ESCAPED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(movie_id, genre_id);

SELECT ROW_COUNT() AS movie_genres_loaded;


SELECT 'Loading ratings; this may take several minutes...' AS status;

LOAD DATA LOCAL INFILE
'/Users/yoey_danjuma/Desktop/DSCI551/dsci551-movie-database/data/staging/load/ratings.csv'
INTO TABLE ratings
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
ESCAPED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(user_id, movie_id, rating, rated_at);

SELECT ROW_COUNT() AS ratings_loaded;


SET UNIQUE_CHECKS = 1;
SET FOREIGN_KEY_CHECKS = 1;

SELECT 'Data loading complete.' AS status;
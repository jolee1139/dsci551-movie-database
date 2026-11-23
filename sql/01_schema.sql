USE movie_database;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS movie_genres;
DROP TABLE IF EXISTS ratings;
DROP TABLE IF EXISTS genres;
DROP TABLE IF EXISTS movies;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS movie_details;

SET FOREIGN_KEY_CHECKS = 1;


CREATE TABLE movie_details (
    tmdb_id INT UNSIGNED PRIMARY KEY,
    imdb_id VARCHAR(20),
    tmdb_title VARCHAR(500) NOT NULL,
    original_title VARCHAR(500),
    overview TEXT,
    release_date DATE,
    runtime_minutes SMALLINT UNSIGNED,
    budget BIGINT UNSIGNED,
    revenue BIGINT UNSIGNED,
    original_language VARCHAR(10),
    popularity DOUBLE,
    vote_average DECIMAL(4, 2),
    vote_count INT UNSIGNED,
    status VARCHAR(50),
    tagline VARCHAR(500),
    poster_path VARCHAR(255)
) ENGINE = InnoDB;


CREATE TABLE users (
    user_id INT UNSIGNED PRIMARY KEY
) ENGINE = InnoDB;


CREATE TABLE movies (
    movie_id INT UNSIGNED PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    release_year SMALLINT UNSIGNED,
    tmdb_id INT UNSIGNED,

    INDEX idx_movies_tmdb_id (tmdb_id),

    CONSTRAINT fk_movies_tmdb
        FOREIGN KEY (tmdb_id)
        REFERENCES movie_details (tmdb_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
) ENGINE = InnoDB;


CREATE TABLE genres (
    genre_id SMALLINT UNSIGNED PRIMARY KEY,
    genre_name VARCHAR(50) NOT NULL UNIQUE
) ENGINE = InnoDB;


CREATE TABLE movie_genres (
    movie_id INT UNSIGNED NOT NULL,
    genre_id SMALLINT UNSIGNED NOT NULL,

    PRIMARY KEY (movie_id, genre_id),
    INDEX idx_movie_genres_genre_id (genre_id),

    CONSTRAINT fk_movie_genres_movie
        FOREIGN KEY (movie_id)
        REFERENCES movies (movie_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT fk_movie_genres_genre
        FOREIGN KEY (genre_id)
        REFERENCES genres (genre_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
) ENGINE = InnoDB;


CREATE TABLE ratings (
    user_id INT UNSIGNED NOT NULL,
    movie_id INT UNSIGNED NOT NULL,
    rating DECIMAL(2, 1) NOT NULL,
    rated_at DATETIME NOT NULL,

    PRIMARY KEY (user_id, movie_id),
    INDEX idx_ratings_movie_id (movie_id),

    CONSTRAINT chk_ratings_value
        CHECK (rating BETWEEN 0.5 AND 5.0),

    CONSTRAINT fk_ratings_user
        FOREIGN KEY (user_id)
        REFERENCES users (user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT fk_ratings_movie
        FOREIGN KEY (movie_id)
        REFERENCES movies (movie_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
) ENGINE = InnoDB;
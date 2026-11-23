USE movie_database;


/* Build reusable movie-level rating statistics. */

DROP TEMPORARY TABLE IF EXISTS movie_rating_stats;

CREATE TEMPORARY TABLE movie_rating_stats AS
SELECT
    movie_id,
    COUNT(*) AS rating_count,
    SUM(rating) AS rating_sum,
    AVG(rating) AS average_rating
FROM ratings
GROUP BY movie_id;

ALTER TABLE movie_rating_stats
    ADD PRIMARY KEY (movie_id);


/* Query 1: Movies with the most MovieLens ratings. */

SELECT 'Query 1: Most-rated movies' AS analysis;

SELECT
    m.movie_id,
    m.title,
    m.release_year,
    s.rating_count,
    ROUND(s.average_rating, 2) AS average_rating
FROM movie_rating_stats AS s
JOIN movies AS m
    ON m.movie_id = s.movie_id
ORDER BY
    s.rating_count DESC,
    m.movie_id
LIMIT 10;


/* Query 2: Highest-rated popular movies and their genres. */

SELECT 'Query 2: Highest-rated popular movies' AS analysis;

SELECT
    m.movie_id,
    m.title,
    m.release_year,
    GROUP_CONCAT(
        g.genre_name
        ORDER BY g.genre_name
        SEPARATOR ', '
    ) AS genres,
    s.rating_count,
    ROUND(s.average_rating, 2) AS average_rating
FROM movie_rating_stats AS s
JOIN movies AS m
    ON m.movie_id = s.movie_id
LEFT JOIN movie_genres AS mg
    ON mg.movie_id = m.movie_id
LEFT JOIN genres AS g
    ON g.genre_id = mg.genre_id
WHERE s.rating_count >= 5000
GROUP BY
    m.movie_id,
    m.title,
    m.release_year,
    s.rating_count,
    s.average_rating
ORDER BY
    average_rating DESC,
    s.rating_count DESC
LIMIT 15;


/* Query 3: Rating behavior by genre. */

SELECT 'Query 3: Genre performance' AS analysis;

SELECT
    g.genre_name,
    COUNT(*) AS movie_count,
    SUM(s.rating_count) AS rating_count,
    ROUND(
        SUM(s.rating_sum) / SUM(s.rating_count),
        2
    ) AS average_rating
FROM genres AS g
JOIN movie_genres AS mg
    ON mg.genre_id = g.genre_id
JOIN movie_rating_stats AS s
    ON s.movie_id = mg.movie_id
GROUP BY
    g.genre_id,
    g.genre_name
ORDER BY
    average_rating DESC,
    rating_count DESC;


/* Query 4: Movie ratings grouped by release decade. */

SELECT 'Query 4: Ratings by release decade' AS analysis;

SELECT
    FLOOR(m.release_year / 10) * 10 AS decade_start,
    COUNT(*) AS movie_count,
    SUM(s.rating_count) AS rating_count,
    ROUND(
        SUM(s.rating_sum) / SUM(s.rating_count),
        2
    ) AS average_rating
FROM movies AS m
JOIN movie_rating_stats AS s
    ON s.movie_id = m.movie_id
WHERE m.release_year BETWEEN 1900 AND 2029
GROUP BY decade_start
ORDER BY decade_start;


/* Query 5: Largest disagreement between MovieLens and TMDB. */

SELECT 'Query 5: MovieLens versus TMDB ratings' AS analysis;

SELECT
    m.title,
    m.release_year,
    s.rating_count AS movielens_rating_count,
    ROUND(s.average_rating, 2) AS movielens_rating,
    md.vote_count AS tmdb_vote_count,
    md.vote_average AS tmdb_rating_out_of_10,
    ROUND(md.vote_average / 2, 2) AS tmdb_rating_out_of_5,
    ROUND(
        ABS(s.average_rating - md.vote_average / 2),
        2
    ) AS rating_difference
FROM movies AS m
JOIN movie_rating_stats AS s
    ON s.movie_id = m.movie_id
JOIN movie_details AS md
    ON md.tmdb_id = m.tmdb_id
WHERE
    s.rating_count >= 5000
    AND md.vote_count >= 1000
ORDER BY
    rating_difference DESC,
    s.rating_count DESC
LIMIT 15;


/* Query 6: High-return movies with substantial budgets. */

SELECT 'Query 6: Highest financial return' AS analysis;

SELECT
    m.title,
    m.release_year,
    md.budget,
    md.revenue,
    ROUND(md.revenue / md.budget, 2) AS revenue_multiple,
    s.rating_count,
    ROUND(s.average_rating, 2) AS average_rating
FROM movies AS m
JOIN movie_details AS md
    ON md.tmdb_id = m.tmdb_id
JOIN movie_rating_stats AS s
    ON s.movie_id = m.movie_id
WHERE
    md.budget >= 1000000
    AND md.revenue > 0
    AND s.rating_count >= 1000
ORDER BY
    revenue_multiple DESC,
    md.revenue DESC
LIMIT 15;


/* Query 7: Most active MovieLens users. */

SELECT 'Query 7: Most active users' AS analysis;

SELECT
    user_id,
    COUNT(*) AS rating_count,
    ROUND(AVG(rating), 2) AS average_rating_given,
    MIN(rated_at) AS first_rating,
    MAX(rated_at) AS latest_rating
FROM ratings
GROUP BY user_id
ORDER BY
    rating_count DESC,
    user_id
LIMIT 10;


DROP TEMPORARY TABLE IF EXISTS movie_rating_stats;
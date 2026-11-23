USE movie_database;

SELECT 'Baseline trial 2' AS experiment;

EXPLAIN ANALYZE
SELECT
    movie_id,
    COUNT(*) AS rating_count,
    AVG(rating) AS average_rating
FROM ratings FORCE INDEX (idx_ratings_movie_id)
GROUP BY movie_id;


SELECT 'Covering-index trial 2' AS experiment;

EXPLAIN ANALYZE
SELECT
    movie_id,
    COUNT(*) AS rating_count,
    AVG(rating) AS average_rating
FROM ratings FORCE INDEX (idx_ratings_movie_rating)
GROUP BY movie_id;


SELECT 'Baseline trial 3' AS experiment;

EXPLAIN ANALYZE
SELECT
    movie_id,
    COUNT(*) AS rating_count,
    AVG(rating) AS average_rating
FROM ratings FORCE INDEX (idx_ratings_movie_id)
GROUP BY movie_id;


SELECT 'Covering-index trial 3' AS experiment;

EXPLAIN ANALYZE
SELECT
    movie_id,
    COUNT(*) AS rating_count,
    AVG(rating) AS average_rating
FROM ratings FORCE INDEX (idx_ratings_movie_rating)
GROUP BY movie_id;
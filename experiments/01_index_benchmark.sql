USE movie_database;

-- If a previous run was interrupted, run: DROP INDEX idx_ratings_movie_id ON ratings;

-- Create the temporary non-covering index used for the baseline tests.
CREATE INDEX idx_ratings_movie_id
    ON ratings (movie_id);


SELECT 'Baseline trial 1' AS experiment;

EXPLAIN ANALYZE
SELECT
    movie_id,
    COUNT(*) AS rating_count,
    AVG(rating) AS average_rating
FROM ratings FORCE INDEX (idx_ratings_movie_id)
GROUP BY movie_id;


SELECT 'Covering-index trial 1' AS experiment;

EXPLAIN ANALYZE
SELECT
    movie_id,
    COUNT(*) AS rating_count,
    AVG(rating) AS average_rating
FROM ratings FORCE INDEX (idx_ratings_movie_rating)
GROUP BY movie_id;


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


SELECT 'Full-table-scan trial 1' AS experiment;

EXPLAIN ANALYZE
SELECT
    movie_id,
    COUNT(*) AS rating_count,
    AVG(rating) AS average_rating
FROM ratings
IGNORE INDEX (idx_ratings_movie_id, idx_ratings_movie_rating)
GROUP BY movie_id;


SELECT 'Full-table-scan trial 2' AS experiment;

EXPLAIN ANALYZE
SELECT
    movie_id,
    COUNT(*) AS rating_count,
    AVG(rating) AS average_rating
FROM ratings
IGNORE INDEX (idx_ratings_movie_id, idx_ratings_movie_rating)
GROUP BY movie_id;


SELECT 'Full-table-scan trial 3' AS experiment;

EXPLAIN ANALYZE
SELECT
    movie_id,
    COUNT(*) AS rating_count,
    AVG(rating) AS average_rating
FROM ratings
IGNORE INDEX (idx_ratings_movie_id, idx_ratings_movie_rating)
GROUP BY movie_id;


-- Show which access path MySQL chooses naturally while both indexes exist.
SELECT 'Unhinted optimizer plan' AS experiment;

EXPLAIN FORMAT=TREE
SELECT
    movie_id,
    COUNT(*) AS rating_count,
    AVG(rating) AS average_rating
FROM ratings
GROUP BY movie_id;


-- Restore the database to the state created by 01_schema.sql.
DROP INDEX idx_ratings_movie_id
    ON ratings;
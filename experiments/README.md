
# Ratings Index Performance Experiment

## Objective

Measure whether a covering index on `ratings(movie_id, rating)`
improves the performance of a movie-level rating aggregation compared
with the required foreign-key index on `ratings(movie_id)`.

## Environment

- MySQL Community Server 9.6.0
- Apple Silicon MacBook Air
- 20,000,263 rating records
- 26,744 rated movies

## Test query

```sql
SELECT
    movie_id,
    COUNT(*) AS rating_count,
    AVG(rating) AS average_rating
FROM ratings
GROUP BY movie_id;
```

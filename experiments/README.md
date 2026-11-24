## Results: three access paths for the same query

| Access path | Plan operations | Median time |
|---|---|---:|
| Forced non-covering index `(movie_id)` | Index scan → Group aggregate | 184,311 ms |
| No secondary index (full table scan) | Table scan → Aggregate using temporary table | 8,814 ms |
| Covering index `(movie_id, rating)` | Covering index scan → Group aggregate | 4,137 ms |

*Every reported time is the median of three trials. The table-scan trials were executed last, after the InnoDB buffer pool had already been warmed by the indexed trials.*

## Why the non-covering index is slowest

In InnoDB, each entry in the secondary index contains `movie_id` plus the table's primary key, `(user_id, movie_id)`. Because the index does not contain `rating`, MySQL must use that primary key to retrieve the value from the **clustered index**, which is the primary-key B+ tree containing the complete rows.

The secondary index is scanned in `movie_id` order, while the clustered index is ordered primarily by `user_id`. Consequently, successive row lookups often jump to unrelated locations in the clustered index, producing **random I/O**. This query requires one clustered-index lookup for every rating row—20,000,263 lookups—which makes the non-covering index the slowest access path.

## Why a full table scan beats the non-covering index

A full table scan reads the clustered-index leaf pages using mostly **sequential I/O**, obtaining both `movie_id` and `rating` directly without performing a separate clustered-index lookup for every row. Although MySQL must build a temporary table to group records by `movie_id`, this is still substantially faster than 20 million random lookups.

The benchmark's full-table-scan plan finished in approximately 8.81 seconds. As additional evidence that sequential access is efficient, Query 7 also read all 20,000,263 rating rows sequentially in approximately 3.8 seconds.

## Why the covering index is fastest

The covering index `(movie_id, rating)` contains every column required to calculate the rating count and average. Its entries are ordered by `movie_id`, allowing MySQL to scan the index and perform the grouped aggregation directly without retrieving rows from the clustered index or building a temporary grouping table.

Because InnoDB adds primary-key columns to every secondary index entry, the physical entry contains `(movie_id, rating)` plus `user_id`; `movie_id` does not need to be added again because it is already part of the index key. These entries are still narrower than the complete clustered-index records because the scan excludes `rated_at` and avoids reading the full row structure, reducing the number of B+ tree pages and the amount of I/O required.

## Optimizer behavior

In the unhinted plan, MySQL independently selected a covering index scan using `idx_ratings_movie_rating`. This confirms that, when both secondary indexes were available, the optimizer naturally chose the fastest access path.

For the forced plans, MySQL estimated costs of `25.3e6` to `26.6e6` for the non-covering index and `24.2e6` for the covering index—a difference of less than 10%. However, their measured median times differed by approximately 45×: 184,311 ms versus 4,137 ms. This indicates that the cost model badly underestimated the expense of performing 20 million random lookups into the clustered index.

Cost estimates should also be compared only within the same optimization mode. The same covering-index plan had an estimated cost of `24.2e6` when forced but only `6.63e6` when selected without a hint. Optimizer costs are not execution times, so they must be checked against measured results.
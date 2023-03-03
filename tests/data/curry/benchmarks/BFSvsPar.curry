-- Benchmark to compare BFS vs. Parallel Search

-- f n = loop n ? n ? loop n
--  where
--   loop i = loop (i+1)
-- 
-- -- The goal (f 0) should loop with BFS but should deliver a solution
-- -- with parallel search.
-- -- However, in the current implementation, it loops even with parallel search.
-- main | f 0 == 25 = success
-- 

bin n = bin (2*n+1) ? bin (2*n) ? n
main | bin 0 == 1000000 = success

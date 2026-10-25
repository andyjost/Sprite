-- Select has named input sizes but no main; use its smallest workload.
module SelectBench where
import qualified Select
main :: Int
main = Select.select_50

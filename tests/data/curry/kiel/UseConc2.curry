-- Due to import qualification, the name "+" from the prelude
-- is still visible without qualification:

import qualified ModConc

main1 :: [Int]
main1 = (ModConc..+.) [1] [1+1]
--main1 = [1] ModConc..+. [1+1]

main2 :: [Int]
main2 = ModConc.conc [1] [2]

-- Nullary expressions from the properties/examples in TestPrelude.curry.
module TestPreludeGoals where

import TestPrelude

-- Source states: 5
checkPlus = (2+3)

-- Source states: (-4)
checkMinus = (1 - 5)

-- Source states: GT
checkCompare1 = (compare True False)

-- Source states: LT
checkCompare2 = (compare 3 4)

-- Source states: LT
checkCompare3 = (compare Nothing (Just (not unknown)))

-- Source states: GT
checkCompare4 = (compare (True,failed) (False,True))

-- Source states: LT
checkCompare6 = (compare 'A' 'a')

-- Source states: GT
checkCompare7 = (compare "AAB" "AA")

-- Source states: 2
checkDiv1 = (13 `div` 5)

-- Source states: (-4)
checkDiv2 = (15 `div` (-4))

-- Source states: 3
checkMod1 = (13 `mod` 5)

-- Source states: 1
checkMod2 = ((-15) `mod` 4)

-- Source states: 2
checkQuot1 = (13 `quot` 5)

-- Source states: (-3)
checkQuot2 = (15 `quot` (-4))

-- Source states: 3
checkRem1 = (13 `rem` 5)

-- Source states: (-3)
checkRem2 = ((-15) `rem` 4)

-- Source states: (3,1)
checkDivMod1 = (divMod 7 2)

-- Source states: (-4,-1)
checkDivMod2 = (divMod 7 (-2))

-- Source states: (3,1)
checkQuotRem1 = (quotRem 7 2)

-- Source states: (-3,1)
checkQuotRem2 = (quotRem 7 (-2))

-- Source states: no values
comparePartial = compare (True,failed) (True,True)

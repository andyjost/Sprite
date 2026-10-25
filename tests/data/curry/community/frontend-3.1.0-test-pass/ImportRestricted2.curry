module ImportRestricted2 where

import ImportRestricted
import ImportRestrictedExport (Test(Test))

testexpr1 :: Test
testexpr1 = Test testexpr1

testexpr2 :: Test
testexpr2 = test testexpr1

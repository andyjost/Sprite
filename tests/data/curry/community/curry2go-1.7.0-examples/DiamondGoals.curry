-- Finite instances of the unchanged upstream examples/properties.
module DiamondGoals where

import Diamond

-- Derived harness expectation: 1 (decimal width)
oneDigit = size 7

-- Derived harness expectation: 2 (decimal width)
twoDigits = size 42

-- Derived harness expectation: IO: one line containing 1
diamondOne = diamond 1


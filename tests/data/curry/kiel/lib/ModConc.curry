-- This module defines list concatenation several times

module ModConc(conc,(+),(.+.)) where

infixr 5 +,.+.

(+) :: [a] -> [a] -> [a]
a + b = a Prelude.++ b

(.+.) :: [a] -> [a] -> [a]
a .+. b = a + b

conc :: [a] -> [a] -> [a]
conc = (+)


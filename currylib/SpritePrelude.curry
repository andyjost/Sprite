-- Boolean values
data Bool = False | True

--- Sequential conjunction on Booleans.
(&&)            :: Bool -> Bool -> Bool
True  && x      = x
False && _      = False
 

--- Sequential disjunction on Booleans.
(||)            :: Bool -> Bool -> Bool
True  || _      = True
False || x      = x
 

--- Negation on Booleans.
not             :: Bool -> Bool
not True        = False
not False       = True


-- Exclusive or.
xor             :: Bool -> Bool -> Bool
xor True True   = False
xor True False  = True
xor False True  = True
xor False False = False

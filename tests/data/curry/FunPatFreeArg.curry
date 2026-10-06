-- Programs for unit_funpat_free_argument.py.
--
-- A function with a functional pattern, called with a free variable in that
-- argument position, binds the variable.  The rule of Antoy and Hanus
-- ("Declarative Programming with Function Patterns", LOPSTR 2005): a pattern
-- side c t1..tn against a free actual binds the variable to c x1..xn with
-- fresh variables and continues with the components; a primitive value
-- binds the variable to the value.  FunPatFreeArgSet reads the same
-- programs through set functions; this module does not import
-- Control.SetFunctions, so the PAKCS oracle loads it.

import Data.Char (toUpper)

-- A non-linear functional pattern over strings: the pattern rule of make.
rule :: String -> [String] -> String
rule (stem ++ ".o") [stem ++ ".c"] = "cc"

-- The desugaring written out: the pattern side on the left of =:<=.
rule7 :: String -> [String] -> String
rule7 (stem ++ ".o") ins | [stem ++ ".c"] =:<= ins = "cc7"

-- The free variable on the pattern side.
rule8 :: String -> [String] -> String
rule8 (stem ++ ".o") ins | ins =:<= [stem ++ ".c"] = "cc8"

-- The strict guard.
rule1 :: String -> [String] -> String
rule1 (stem ++ ".o") ins | ins =:= [stem ++ ".c"] = "cc1"

-- The free variable created inside the function: the value carries it
-- bound.
cand :: (String -> [String] -> String) -> String -> ([String], String)
cand f t = (ins, f t ins) where ins free

-- A linear functional pattern: the pattern shares no variable with another
-- argument.  The front end matches Just by a case, which narrows the free
-- actual, and writes one =:<= for the sub-pattern, id 3 =:<= x, with no
-- tuple: the Int value binds the component.
single :: Maybe Int -> String
single (Just (id 3)) = "three"

singleC :: (Maybe Int, String)
singleC = (m, single m) where m free

-- An Int list.  The second pattern is a call that gives an Int, so the free
-- actual is bound to a value.
count :: [Int] -> [Int] -> String
count (xs ++ [0]) [length xs] = "count"

countC :: [Int] -> ([Int], String)
countC xs = (ins, count xs ins) where ins free

-- Maybe: a constructor-rooted pattern with a call inside.
wrap :: Int -> Maybe Int -> String
wrap n (Just (n + 1)) = "succ"

wrapC :: Int -> (Maybe Int, String)
wrapC n = (m, wrap n m) where m free

-- A small data type with two constructors.
data Shape = Circle Int | Rect Int Int
  deriving (Eq, Ord, Show)

double :: Shape -> Shape -> String
double (Circle r) (Rect (2 * r) (2 * r)) = "rect"

doubleC :: Shape -> (Shape, String)
doubleC s = (t, double s t) where t free

-- A Char: the pattern side is a primitive value.
upper :: String -> Char -> String
upper (c : _) (toUpper c) = "upper"

upperC :: String -> (Char, String)
upperC s = (ch, upper s ch) where ch free

-- A Float: the pattern side is a primitive value of the third builtin type.
half :: Int -> Float -> String
half n (fromInt n / 2.0) = "half"

halfC :: Int -> (Float, String)
halfC n = (x, half n x) where x free

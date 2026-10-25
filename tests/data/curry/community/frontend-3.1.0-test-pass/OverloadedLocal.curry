module OverloadedLocal where

test :: Show a => a -> ([a] -> Bool) -> Prop
test x f = Prop [Test res [] []]
 where
  xs  = [x]
  res = case [f xs] of
          bs      -> Ambigious bs (map show xs)

data Prop = Prop [Test]

data Test = Test Result [String] [String]

data Result = Undef | Ok | Falsified [String] | Ambigious [Bool] [String]

setResult :: Result -> Test -> Test
setResult res (Test _ s a) = Test res a s

import Control.SetFunctions
data Result = GT | GF | HT | HF deriving (Eq, Ord, Show)

f = g ? h
g True = GT
g False = GF
h True = HT
h False = HF

arg = True ? False

goal0 = sortValues (set1 g arg) -- [GT] ? [GF]
goal1 = sortValues (set1 f arg) -- [GT,HT] ? [GF,HF]

-- ([GT],[GT,HT]) ? ([GT],[GF,HF]) ? ([GF],[GT,HT]) ? ([GF],[GF,HF])
main = (goal0, goal1)


import SetFunctions
data Result = GT | GF | HT | HF

f = g ? h
g True = GT
g False = GF
h True = HT
h False = HF

arg = True ? False

goal0 = (set1 g arg) -- [GT] ? [GF]
goal1 = (set1 f arg) -- [GT,HT] ? [GF,HF]

-- ([GT],[GT,HT]) ? ([GT],[GF,HF]) ? ([GF],[GT,HT]) ? ([GF],[GF,HF])
main = (allValues goal0, allValues goal1)


import SetFunctions
eval = allValues

-- PACKS, KiCS2 both return [True,False]
f True True   = "fTT"
f True False  = "fTF"
f False True  = "fFT"
f False False = "fFF"
a = True ? False
goal0a = eval $ set1 (\x -> x a a) f
goal0b = eval $ set1 (\x -> let y = a in x y y) f
goal0c = eval $ set2 (\x y -> x y a) f True
goal0d = eval $ set2 (\x y -> x y a) f a

g True True   = "gTT"
g True False  = "gTF"
g False True  = "gFT"
g False False = "gFF"
goal1a = eval $ set1 (\x -> x a a) (f ? g)
goal1b = eval $ set1 (\x -> let y = a in x y y) (f ? g)
goal1c = eval $ set2 (\x y -> x y a) (f ? g) True
goal1d = eval $ set2 (\x y -> x y a) (f ? g) a

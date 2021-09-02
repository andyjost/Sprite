import Control.SetFunctions

data Result = F_TT | F_TF | F_FT | F_FF | G_TT | G_TF | G_FT | G_FF
    deriving (Eq, Ord, Show)

f True True   = F_TT
f True False  = F_TF
f False True  = F_FT
f False False = F_FF
a = True ? False
goal00 = sortValues $ set1 (\x -> x a a) f
goal01 = sortValues $ set1 (\x -> let y = a in x y y) f
goal02 = sortValues $ set2 (\x y -> x y a) f True
goal03 = sortValues $ set2 (\x y -> x y a) f a

g True True   = G_TT
g True False  = G_TF
g False True  = G_FT
g False False = G_FF
goal10 = sortValues $ set1 (\x -> x a a) (f ? g)
goal11 = sortValues $ set1 (\x -> let y = a in x y y) (f ? g)
goal12 = sortValues $ set2 (\x y -> x y a) (f ? g) True
goal13 = sortValues $ set2 (\x y -> x y a) (f ? g) a

a = True ? False
comb b = b ? not b
k b = [b, a]

data Result1 = G_T | G_F | H_T | H_F deriving (Eq, Ord, Show)

f1 = g1 ? h1
g1 True = G_T
g1 False = G_F
h1 True = H_T
h1 False = H_F

data Result2 = G_TT | G_TF | G_FT | G_FF | H_TT | H_TF | H_FT | H_FF
    deriving (Eq, Ord, Show)

f2 = g2 ? h2
g2 True True   = G_TT
g2 True False  = G_TF
g2 False True  = G_FT
g2 False False = G_FF
h2 True True   = H_TT
h2 True False  = H_TF
h2 False True  = H_FT
h2 False False = H_FF


data ABC = A | B | C deriving (Eq, Ord, Show)
data ResultABC = G_A | G_B | G_C | H_A | H_B | H_C deriving (Eq, Ord, Show)

ab = A ? B
abc = A ? B ? C

f3 = g3 ? h3
g3 A = G_A
g3 B = G_B
g3 C = G_C
h3 A = H_A
h3 B = H_B
h3 C = H_C

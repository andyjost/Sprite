a = True ? False
comb b = b ? not b
k b = [b, a]

narrow True = True
narrow False = False

data Result1 = G_T | G_F | H_T | H_F deriving (Eq, Ord, Show)

f1 = g1 ? h1
f1' x = g1 x ? h1 x
g1 True = G_T
g1 False = G_F
h1 True = H_T
h1 False = H_F

data Result2 = G_TT | G_TF | G_FT | G_FF | H_TT | H_TF | H_FT | H_FF
    deriving (Eq, Ord, Show)

f2 = g2 ? h2
f2' x y = g2 x y ? h2 x y
g2 True True   = G_TT
g2 True False  = G_TF
g2 False True  = G_FT
g2 False False = G_FF
h2 True True   = H_TT
h2 True False  = H_TF
h2 False True  = H_FT
h2 False False = H_FF

data Result3 = G_TTT | G_TTF | G_TFT | G_TFF | G_FTT | G_FTF | G_FFT | G_FFF
             | H_TTT | H_TTF | H_TFT | H_TFF | H_FTT | H_FTF | H_FFT | H_FFF
    deriving (Eq, Ord, Show)

f3 = g3 ? h3
f3' x y z = g3 x y z ? h3 x y z

g3 True  True  True  = G_TTT
g3 True  True  False = G_TTF
g3 True  False True  = G_TFT
g3 True  False False = G_TFF
g3 False True  True  = G_FTT
g3 False True  False = G_FTF
g3 False False True  = G_FFT
g3 False False False = G_FFF

h3 True  True  True  = H_TTT
h3 True  True  False = H_TTF
h3 True  False True  = H_TFT
h3 True  False False = H_TFF
h3 False True  True  = H_FTT
h3 False True  False = H_FTF
h3 False False True  = H_FFT
h3 False False False = H_FFF

data ABC = A | B | C deriving (Eq, Ord, Show)
data ResultABC = G_A | G_B | G_C | H_A | H_B | H_C deriving (Eq, Ord, Show)

ab = A ? B
abc = A ? B ? C

fa = ga ? ha
ga A = G_A
ga B = G_B
ga C = G_C
ha A = H_A
ha B = H_B
ha C = H_C

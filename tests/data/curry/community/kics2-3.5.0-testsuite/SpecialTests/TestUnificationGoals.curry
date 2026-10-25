-- Finite instances of the unchanged upstream examples/properties.
module TestUnificationGoals where

import TestUnification

-- Source expectation: True
checkTest0 = (True =:= True)

-- Source expectation: no values
checkTest1 = (True =:= False)

-- Source expectation: True
checkTest2 = (let x free in x =:= True)

-- Source expectation: True
checkTest3 = (let x free in x =:= True &> x)

-- Source expectation: [True,True]
checkTest4 = (let x free in x =:= True &> [x,x])

-- Source expectation: [True,True]
checkTest5 = (let x free in [x =:= True &> x,x])

-- Source expectation: [True,True]
checkTest6 = (let x free in [x,x =:= True &> x])

-- Source expectation: True
checkTest7 = (let x,y free in uni x y)

-- Source expectation: [True,True]
checkTest8 = (let x,y free in x =:= y &> y=:= True &> [x,y])

-- Source expectation: [True,True]
checkTest9 = (let x,y free in x =:= y &> x=:= True &> [x,y])

-- Source expectation: [False,False]
checkTest10 = (let x,y,z free in x =:= y &> x =:= z &> y=:=False &> [x,y])

-- Source expectation: [False,False,False]
checkTest11 = (let x,y,z free in x =:= y &> x =:= z &> x=:=False &> [z,x,y])

-- Source expectation: [False,False,False]
checkTest12 = (let x,y,z free in x =:= y &> x =:= z &> z=:=False &> [x,z,y])

-- Source expectation: [False,False,False]
checkTest13 = (let x,y,z free in x =:= y &> x =:= z &> z=:=False &> y=:=False &> [x,y,z])

-- Source expectation: False
checkTest14 = (let x,y free in x=:=y &> y=:=False &> x)

-- Source expectation: (False ? True)
checkTest15 = (let x,y free in x=:=(y?True) &> y=:=False &> x)

-- Source expectation: [True]
checkTest16 = (let x free in x=:=[] &> True:x)

-- Source expectation: [True]
checkTest17 = (let x free in x=:=[True] &> x)

-- Source expectation: [True]
checkTest18 = (let x,y free in x=:=y &> (y=:= [True] &> x))

-- Source expectation: no values
checkTest19 = (let x,y free in x=:=y &> y=:= [True] &> f x &> x)

-- Source expectation: [True]
checkTest20 = (let x,y free in x=:=y &> y=:= [True] &> g x &> x)

-- Source expectation: ([True] ? [False])
checkTest21 = (let x,y free in x=:=(y?[False]) &> y=:=[True] &> x)

-- Source expectation: True
checkTest22 = (let x,y free in uni2 x [y])

-- Source expectation: [True]
checkTest24 = (let x,y free in x =:= [y] &> y=:=True &> x)

-- Source expectation: ([False] ? [True])
checkTest26 = (let x,y free in x =:= [y?True] &> y=:=False &> x)

-- Source expectation: [False,True,True]
checkTest27 = (let x,y,z free in [x,True,z]=:=[False,y,y] &> [x,y,z])

-- Source expectation: [True]
checkTest28 = (let x,y free in x =:= (y =:= [True] &> y) &> x)

-- Source expectation: [True]
checkTest29 = (let x,y free in x =:= (True:(y =:= [] &> y)) &> x)

-- Source expectation: no values
checkTest30 = (let x,y free in x =:= [True] &> y =:= [False] &> x =:= y)

-- Source expectation: no values
checkTest31 = (let x,y free in x =:= [] &> y ++ [False] =:= x)

-- Source expectation: no values
checkTest32 = (let x,y1,y2 free in x =:= [] &> y1:(y2 ++ [False]) =:= x)

-- Source expectation: no values
checkTest33 = (let x,y2 free in x =:= [] &> (y2 ++ [False]) =:= x)

-- Source expectation: no values
checkTest34 = (let x,y1 free in x =:= [] &> y1:[False] =:= x)


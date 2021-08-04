module Integer where

toNat :: Int -> Nat
toNat i = if i<=0 then failed else let (q,r) = i `divMod` 2 in
          if q==0 then IHi else (if r==0 then O else I) (toNat q)
toAlgebraicInt :: Int -> AlgebraicInt
toAlgebraicInt i = if i==0 then Zero else if i<0 then Neg (toNat (-i)) else Pos (toNat i)

fromNat :: Nat -> Int
fromNat IHi   = 1
fromNat (O n) = 2 * fromNat n
fromNat (I n) = 2 * fromNat n + 1

fromAlgebraicInt :: AlgebraicInt -> Int
fromAlgebraicInt (Neg n) = - (fromNat n)
fromAlgebraicInt Zero    = 0
fromAlgebraicInt (Pos n) = fromNat n

-- ---------------------------------------------------------------------------
-- Test Cases
-- ---------------------------------------------------------------------------

{-
import Test.EasyCheck

test_cmpNat :: Nat -> Nat -> Prop
test_cmpNat x y = cmpNat x y -=- compare (fromNat x) (fromNat y)

test_succ :: Nat -> Prop
test_succ x = fromNat (succ x) -=- fromNat x + 1

test_pred :: Nat -> Prop
test_pred x = x /= IHi ==> fromNat (pred x) -=- fromNat x - 1

test_addNat :: Nat -> Nat -> Prop
test_addNat x y = fromNat (x +^ y) -=- fromNat x + fromNat y

test_subNat :: Nat -> Nat -> Prop
test_subNat x y = fromAlgebraicInt (x -^ y) -=- fromNat x - fromNat y

test_mult2 :: AlgebraicInt -> Prop
test_mult2 x = fromAlgebraicInt (mult2 x) -=- fromAlgebraicInt x * 2

test_multNat :: Nat -> Nat -> Prop
test_multNat x y = fromNat (x *^ y) -=- fromNat x * fromNat y

test_div2 :: Nat -> Prop
test_div2 x = x /= IHi ==> fromNat (div2 x) -=- fromNat x `div` 2

test_mod2 :: Nat -> Prop
test_mod2 x = fromAlgebraicInt (mod2 x) -=- fromNat x `mod` 2

test_quotRemNat :: Nat -> Nat -> Prop
test_quotRemNat x y =
  let (q, r) = quotRemNat x y
  in  (fromAlgebraicInt q, fromAlgebraicInt r) -=- quotRem (fromNat x) (fromNat y)

test_lteqInteger :: AlgebraicInt -> AlgebraicInt -> Prop
test_lteqInteger x y = lteqInteger x y -=- fromAlgebraicInt x <= fromAlgebraicInt y

test_cmpInteger :: AlgebraicInt -> AlgebraicInt -> Prop
test_cmpInteger x y = cmpInteger x y -=- fromAlgebraicInt x `compare` fromAlgebraicInt y

test_neg :: AlgebraicInt -> Prop
test_neg x = fromAlgebraicInt (neg x) -=- - (fromAlgebraicInt x)

test_inc :: AlgebraicInt -> Prop
test_inc x = fromAlgebraicInt (inc x) -=- fromAlgebraicInt x + 1

test_dec :: AlgebraicInt -> Prop
test_dec x = fromAlgebraicInt (dec x) -=- fromAlgebraicInt x - 1

test_add :: AlgebraicInt -> AlgebraicInt -> Prop
test_add x y = fromAlgebraicInt (x +# y) -=- fromAlgebraicInt x + fromAlgebraicInt y

test_sub :: AlgebraicInt -> AlgebraicInt -> Prop
test_sub x y = fromAlgebraicInt (x -# y) -=- fromAlgebraicInt x - fromAlgebraicInt y

test_mult :: AlgebraicInt -> AlgebraicInt -> Prop
test_mult x y = fromAlgebraicInt (x *# y) -=- fromAlgebraicInt x * fromAlgebraicInt y

test_quotRem :: AlgebraicInt -> AlgebraicInt -> Prop
test_quotRem x y
  = y /= Zero ==>
    let (q, r) = quotRemInteger x y
    in  (fromAlgebraicInt q, fromAlgebraicInt r) -=- quotRem (fromAlgebraicInt x) (fromAlgebraicInt y)

test_divMod :: AlgebraicInt -> AlgebraicInt -> Prop
test_divMod x y
  = y /= Zero ==>
    let (d, m) = divModInteger x y
    in  (fromAlgebraicInt d, fromAlgebraicInt m) -=- divMod (fromAlgebraicInt x) (fromAlgebraicInt y)

test_div :: AlgebraicInt -> AlgebraicInt -> Prop
test_div x y
  = y /= Zero ==>
    fromAlgebraicInt (divInteger x y) -=- div (fromAlgebraicInt x) (fromAlgebraicInt y)

test_mod :: AlgebraicInt -> AlgebraicInt -> Prop
test_mod x y
  = y /= Zero ==>
    fromAlgebraicInt (modInteger x y) -=- mod (fromAlgebraicInt x) (fromAlgebraicInt y)

test_quot :: AlgebraicInt -> AlgebraicInt -> Prop
test_quot x y
  = y /= Zero ==>
    fromAlgebraicInt (quotInteger x y) -=- quot (fromAlgebraicInt x) (fromAlgebraicInt y)

test_rem :: AlgebraicInt -> AlgebraicInt -> Prop
test_rem x y
  = y /= Zero ==>
    fromAlgebraicInt (remInteger x y) -=- rem (fromAlgebraicInt x) (fromAlgebraicInt y)

-}

-- ---------------------------------------------------------------------------
-- Nat
-- ---------------------------------------------------------------------------

--- Algebraic data type to represent natural numbers
data Nat = IHi | O Nat | I Nat deriving (Eq, Show)

--- comparison, O(min (m,n))
cmpNat :: Nat -> Nat -> Ordering
cmpNat IHi   IHi   = EQ
cmpNat IHi   (O _) = LT
cmpNat IHi   (I _) = LT
cmpNat (O _) IHi   = GT
cmpNat (O x) (O y) = cmpNat x y
cmpNat (O x) (I y) = case cmpNat x y of
  EQ    -> LT
  cmpxy -> cmpxy
cmpNat (I _) IHi   = GT
cmpNat (I x) (O y) = case cmpNat x y of
  EQ    -> GT
  cmpxy -> cmpxy
cmpNat (I x) (I y) = cmpNat x y

--- successor, O(n)
succ :: Nat -> Nat
succ IHi    = O IHi        -- 1       + 1 = 2
succ (O bs) = I bs         -- 2*n     + 1 = 2*n + 1
succ (I bs) = O (succ bs)  -- 2*n + 1 + 1 = 2*(n+1)

--- predecessor, O(n)
pred :: Nat -> Nat
pred IHi         = failed     -- 1 has no predecessor
pred (O IHi)     = IHi        -- 2           - 1 = 1
pred (O x@(O _)) = I (pred x) -- 2*2*n       - 1 = 2*(2*n-1) + 1
pred (O (I x))   = I (O x)    -- 2*(2*n + 1) - 1 = 2*2*n + 1
pred (I x)       = O x        -- 2*n + 1      -1 = 2*n

--- addition, O(max (m, n))
(+^) :: Nat -> Nat -> Nat
IHi +^ y   = succ y           -- 1  +  n   = n + 1
O x +^ IHi = I x              -- 2*n + 1   = 2*n + 1
O x +^ O y = O (x +^ y)       -- 2*m + 2*n = 2*(m+n)
O x +^ I y = I (x +^ y)
I x +^ IHi = O (succ x)
I x +^ O y = I (x +^ y)
I x +^ I y = O (succ x +^ y)

--- subtraction
(-^) :: Nat -> Nat -> AlgebraicInt
IHi     -^ y     = inc (Neg y)           -- 1-n = 1+(-n)
x@(O _) -^ IHi   = Pos (pred x)          --
(O x)   -^ (O y) = mult2 (x -^ y)
(O x)   -^ (I y) = dec (mult2 (x -^ y))
(I x)   -^ IHi   = Pos (O x)
(I x)   -^ (O y) = inc (mult2 (x -^ y))  -- 2*n+1 - 2*m = 1+2*(n-m)
(I x)   -^ (I y) = mult2 (x -^ y)        -- 2*n+1 - (2*m+1) = 2*(n-m)

--- multiplication by 2
mult2 :: AlgebraicInt -> AlgebraicInt
mult2 (Pos n) = Pos (O n)
mult2 Zero    = Zero
mult2 (Neg n) = Neg (O n)

--- multiplication, O(m*n)
(*^) :: Nat -> Nat -> Nat
IHi   *^ y = y
(O x) *^ y = O (x *^ y)
(I x) *^ y = y +^ (O (x *^ y))
-- (I x) *^ IHi = I x
-- (I x) *^ (O y) = (O y) +^ (O (x *^ (O y))) = O (y +^ (x *^ (O y)))
-- (I x) *^ (I y) = (I y) +^ (O (x *^ (I y))) = I (y +^ (x *^ (I y)))

--- division by 2
div2 :: Nat -> Nat
div2 IHi   = failed -- 1 div 2 is not defined for Nat
div2 (O x) = x
div2 (I x) = x

--- modulo by 2
mod2 :: Nat -> AlgebraicInt
mod2 IHi   = Pos IHi
mod2 (O _) = Zero
mod2 (I _) = Pos IHi

--- quotient and remainder
quotRemNat :: Nat -> Nat -> (AlgebraicInt, AlgebraicInt)
quotRemNat x y
  | y == IHi  = (Pos x, Zero   ) -- quotRemNat x 1 = (x, 0)
  | x == IHi  = (Zero , Pos IHi) -- quotRemNat 1 y = (0, 1)
  | otherwise = case cmpNat x y of
      EQ -> (Pos IHi, Zero )   -- x = y : quotRemNat x y = (1, 0)
      LT -> (Zero   , Pos x)   -- x < y : quotRemNat x y = (0, x)
      GT -> case quotRemNat (div2 x) y of
        (Neg _, _    ) -> error "quotRemNat: negative quotient"
        (Zero , _    ) -> (Pos IHi  , x -^ y) -- x > y, x/2 < y  : quotRemNat x y = (1, x - y)
        (Pos _, Neg _) -> error "quotRemNat: negative remainder"
        (Pos d, Zero ) -> (Pos (O d), mod2 x)
        (Pos d, Pos m) -> case quotRemNat (shift x m) y of
          (Neg _ , _ ) -> error "quotRemNat: negative quotient"
          (Zero  , m') -> (Pos (O d)      , m')
          (Pos d', m') -> (Pos (O d +^ d'), m')
  where
    shift IHi   _ = error "quotRemNat.shift: IHi"
    shift (O _) n = O n
    shift (I _) n = I n

-- ---------------------------------------------------------------------------
-- Integer
-- ---------------------------------------------------------------------------

--- Algebraic data type to represent integers
data AlgebraicInt = Neg Nat | Zero | Pos Nat deriving (Eq, Show)

--- less-than-or-equal on AlgebraicInt
lteqInteger :: AlgebraicInt -> AlgebraicInt -> Bool
lteqInteger x y = cmpInteger x y /= GT

--- comparison on AlgebraicInt, O(min (m, n))
cmpInteger :: AlgebraicInt -> AlgebraicInt -> Ordering
cmpInteger Zero    Zero    = EQ
cmpInteger Zero    (Pos _) = LT
cmpInteger Zero    (Neg _) = GT
cmpInteger (Pos _) Zero    = GT
cmpInteger (Pos x) (Pos y) = cmpNat x y
cmpInteger (Pos _) (Neg _) = GT
cmpInteger (Neg _) Zero    = LT
cmpInteger (Neg _) (Pos _) = LT
cmpInteger (Neg x) (Neg y) = cmpNat y x

--- Unary minus. Usually written as "- e".
neg :: AlgebraicInt -> AlgebraicInt
neg Zero    = Zero
neg (Pos x) = Neg x
neg (Neg x) = Pos x

--- increment
inc :: AlgebraicInt -> AlgebraicInt
inc Zero        = Pos IHi
inc (Pos n)     = Pos (succ n)
inc (Neg IHi)   = Zero
inc (Neg (O n)) = Neg (pred (O n))
inc (Neg (I n)) = Neg (O n)

--- decrement
dec :: AlgebraicInt -> AlgebraicInt
dec Zero        = Neg IHi
dec (Pos IHi)   = Zero
dec (Pos (O n)) = Pos (pred (O n))
dec (Pos (I n)) = Pos (O n)
dec (Neg n)     = Neg (succ n)

--- Adds two AlgebraicInts.
(+#)   :: AlgebraicInt -> AlgebraicInt -> AlgebraicInt
Zero      +# x     = x
x@(Pos _) +# Zero  = x
Pos x     +# Pos y = Pos (x +^ y)
Pos x     +# Neg y = x -^ y
x@(Neg _) +# Zero  = x
Neg x     +# Pos y = y -^ x
Neg x     +# Neg y = Neg (x +^ y)

--- Subtracts two AlgebraicInts.
(-#)   :: AlgebraicInt -> AlgebraicInt -> AlgebraicInt
x -# Zero  = x
x -# Pos y = x +# Neg y
x -# Neg y = x +# Pos y

--- Multiplies two AlgebraicInts.
(*#)   :: AlgebraicInt -> AlgebraicInt -> AlgebraicInt
Zero  *# _     = Zero
Pos _ *# Zero  = Zero
Pos x *# Pos y = Pos (x *^ y)
Pos x *# Neg y = Neg (x *^ y)
Neg _ *# Zero  = Zero
Neg x *# Pos y = Neg (x *^ y)
Neg x *# Neg y = Pos (x *^ y)

--- Quotient and Remainder, truncated against zero
quotRemInteger :: AlgebraicInt -> AlgebraicInt -> (AlgebraicInt, AlgebraicInt)
quotRemInteger _       Zero    = failed -- division by zero is not defined
quotRemInteger Zero    (Pos _) = (Zero, Zero)
quotRemInteger Zero    (Neg _) = (Zero, Zero)
quotRemInteger (Pos x) (Pos y) = quotRemNat x y
quotRemInteger (Neg x) (Pos y) = let (d, m) = quotRemNat x y in (neg d, neg m)
quotRemInteger (Pos x) (Neg y) = let (d, m) = quotRemNat x y in (neg d,     m)
quotRemInteger (Neg x) (Neg y) = let (d, m) = quotRemNat x y in (d    , neg m)

--- Quotient and Remainder, truncated against negative infinity
divModInteger :: AlgebraicInt -> AlgebraicInt -> (AlgebraicInt, AlgebraicInt)
divModInteger _       Zero    = failed -- division by zero is not defined
divModInteger Zero    (Pos _) = (Zero, Zero)
divModInteger Zero    (Neg _) = (Zero, Zero)
divModInteger (Pos x) (Pos y) = quotRemNat x y
divModInteger (Neg x) (Pos y) = let (d, m) = quotRemNat x y in case m of
  Zero -> (neg d, m)
  _    -> (neg (inc d), (Pos y) -# m)
divModInteger (Pos x) (Neg y) = let (d, m) = quotRemNat x y in case m of
  Zero -> (neg d, m)
  _    -> (neg (inc d), m -# (Pos y))
divModInteger (Neg x) (Neg y) = let (d, m) = quotRemNat x y in (d, neg m)

--- Integer divisor, truncated towards negative infinity.
divInteger :: AlgebraicInt -> AlgebraicInt -> AlgebraicInt
divInteger x y = fst (divModInteger x y)

--- Integer modulo, truncated towards negative infinity.
modInteger :: AlgebraicInt -> AlgebraicInt -> AlgebraicInt
modInteger x y = snd (divModInteger x y)

--- Integer quotient, truncated towards zero.
quotInteger :: AlgebraicInt -> AlgebraicInt -> AlgebraicInt
quotInteger x y = fst (quotRemInteger x y)

--- Integer remainder, truncated towards zero.
remInteger :: AlgebraicInt -> AlgebraicInt -> AlgebraicInt
remInteger x y = snd (quotRemInteger x y)

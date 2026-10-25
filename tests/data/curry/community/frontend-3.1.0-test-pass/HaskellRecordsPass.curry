-- data
data D = C1 Int
       | C2 String
       | C3 Bool
data RD1 = RD1 {}
data RD2 = RD2 { x,y,z :: Int, a :: Bool, r :: RD1 }
data RD3 a = RD3 { f :: a }

-- newtype
newtype RN = RN { x' :: Int }

-- record construction
r1 = RD1 { }
r2 = RD2 { x = 12, y = 24, z = 34, a = False, r = r1 }
r3 = RD3 { f = r2 }

-- record selection
i = x r2

-- record update
r2' = r2 { x = 12, y = 72 }
r3' = (f r3) { x = 12, y = 72 }

-- record pattern
f' RD2 { x = 45 } = True
f' RD2 { x = 45, a = False } = True
f' RD2 { } = True

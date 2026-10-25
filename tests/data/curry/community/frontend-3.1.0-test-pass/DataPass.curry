data Test1   = Test1 (Test2 Int)

data Test2 a = Test2 Test1 a (a -> a)

data Identity a = Identity a

freeTest1 :: Identity Int
freeTest1 = a where a free

freeTest2 :: Data a => Identity a
freeTest2 = unknown

freeTest3 :: (Int, Bool)
freeTest3 = (aValue, aValue)

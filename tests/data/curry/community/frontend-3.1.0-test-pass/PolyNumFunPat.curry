test1 :: (Data a, Num a, Num b) => a -> b
test1 (id 5) = 1

-- test2 :: (Data a, Num a, Num b) => a -> b
test2 (id 5) = 1

test3 :: (Data a, Num a, Num b) => a -> b
test3 (id _) = 1

-- test4 :: (Data a, Num a, Num b) => a -> b
test4 (id _) = 1

test5 :: Num b => Int -> b
test5 (id _) = 1

-- test6 :: Num b => Int -> b
test6 (id 6) = 1

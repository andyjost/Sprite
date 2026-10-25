-- Example of class and instance definition

class Addable a where
  (+) :: a ->  a  -> a

instance Addable Int where
  x + y = x Prelude.+ y

instance Addable a => Addable [a] where
  xs + ys = zipWith (+) xs ys

testv :: [Int]
testv = [1,2,3] + [4,5,6]

------------------------------------------------------------------

data Matrix a = Matrix [[a]]

instance Addable a => Addable (Matrix a) where
  (Matrix xs) + (Matrix ys) = Matrix (zipWith (zipWith (+)) xs ys)

main :: Matrix Int
main = Matrix [[1,2],[3,4]] + Matrix [[5,6],[7,8]]


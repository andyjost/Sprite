-- A hierarchical module imported by Classes.  Its interface lies under
-- .curry/<subdir>/Sub/Deep.fint, which exercises the interface finder.
module Sub.Deep (Deep (..), deep, unwrapDeep) where

data Deep = Deep Int
  deriving (Eq, Show)

deep :: Int -> Int
deep n = n * 3

unwrapDeep :: Deep -> Int
unwrapDeep (Deep n) = n

hidden :: Int
hidden = 7

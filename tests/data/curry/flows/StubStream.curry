module StubStream where

import Sprite.Stream

whole :: IO Int
whole = yield [1, 2 :: Int] >> return 42

priorError :: IO ()
priorError = yield (1 :: Int) >> yield (2 ? 3 :: Int)

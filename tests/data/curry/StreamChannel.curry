module StreamChannel where

import Sprite.Stream
import Control.SetFunctions

data Box a = Box a
instance Show a => Show (Box a) where
  show (Box x) = "boxed:" ++ show x

three :: IO Int
three = mapM_ yield [1, 2, 3 :: Int] >> return 42

whole :: IO ()
whole = yield ([] :: [Int]) >> yield "" >> yield ["", "a"]
     >> yield (Box [1,2 :: Int]) >> yield ('x', True)

custom :: IO ()
custom = yield (Box (7 :: Int))

freeOut :: IO ()
freeOut = yield (x :: Int) where x free

choiceAction :: IO ()
choiceAction = yield (1 :: Int) ? yield 2

choiceResult :: IO Int
choiceResult = yield (1 :: Int) >> return (2 ? 3)

nestedChoice :: IO ()
nestedChoice = yield [1, 2 ? 3 :: Int]

insideSet :: IO ()
insideSet = values2list (set0 (yield (1 :: Int))) >>= mapM_ id

setInside :: IO ()
setInside = values2list (set1 (\x -> x ? x+1) (1 :: Int)) >>= mapM_ yield

startFile :: String -> IO ()
startFile path = writeFile path "started" >> yield (1 :: Int)

priorError :: IO ()
priorError = yield (1 :: Int) >> error "stream boom"

recovered :: IO ()
recovered = catch (yield (1 :: Int) >> ioError (userError "caught"))
                  (\_ -> yield (2 :: Int))

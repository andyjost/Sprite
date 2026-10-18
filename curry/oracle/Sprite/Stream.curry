-- Text meaning of the stream channel for PAKCS and KiCS2.
module Sprite.Stream (yield) where

yield :: Show a => a -> IO ()
yield x = putStrLn (show x)

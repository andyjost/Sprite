-- Values handed to the caller of an I/O program, in order.
module Sprite.Stream (yield) where

yield :: Show a => a -> IO ()
yield x = primYield show x

-- Keeping the printer as a function also keeps the type of an empty value.
primYield :: (a -> String) -> a -> IO ()
primYield external

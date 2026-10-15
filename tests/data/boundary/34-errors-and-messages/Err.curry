module Err where

inc :: Int -> Int
inc x = x + 1

boom :: Int
boom = error "boom"

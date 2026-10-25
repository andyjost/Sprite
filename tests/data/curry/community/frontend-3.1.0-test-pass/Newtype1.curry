module Newtype1 where

newtype D a = D a

access :: D a -> a
access (D a1) = a1

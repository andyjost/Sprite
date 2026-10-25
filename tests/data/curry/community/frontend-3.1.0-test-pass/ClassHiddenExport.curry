module ClassHiddenExport (A(methodA), mb) where

class A a where
  methodA :: a
  methodB :: a
  methodB = error ""

mb = methodB

{-# LANGUAGE MultiParamTypeClasses #-}

module InstanceExport.N where

import InstanceExport.M

data U = U

instance C U where
  methodC = U

instance C Bool where
  methodC = True

class D a b where
  methodD :: a -> b -> Bool

instance D T U where
  methodD T U = False

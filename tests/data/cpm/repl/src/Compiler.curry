module Compiler where

import Curry.Compiler.Distribution (curryCompiler)
import Test.Prop

systemName :: Prop
systemName = curryCompiler -=- "sprite"

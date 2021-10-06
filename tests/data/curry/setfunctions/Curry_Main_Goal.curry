{-# OPTIONS_CYMAKE -W no-missing-signatures #-}
import SetFunctions
import Prelude
kics2MainGoal :: (Int,[String],Int)
kics2MainGoal = ( (1+) $## x ,[ "x" ] ,x )  where x free

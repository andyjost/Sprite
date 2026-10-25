module SearchLibraryImport where

import Control.Search.SetFunctions
import qualified Control.Search.Unsafe as Unsafe
import qualified Control.Search.AllValues as AllValues

main :: ([Int], [Int])
main = (sortValues (set0 (1 ? 2)), Unsafe.allValues (7 ? 7))

action :: IO (Maybe Int)
action = AllValues.getOneValue 7

capturedValues :: [Int]
capturedValues = let x = 1 ? 2 in Unsafe.allValues x

capturedFirst :: Maybe Int
capturedFirst = let x = 1 ? 2 in Unsafe.oneValue x

capturedIO :: IO (Maybe Int)
capturedIO = let x = 7 in AllValues.getOneValue x

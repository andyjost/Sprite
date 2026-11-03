module ReadLegacy where
import ReadShowTerm
import Data.Char (chr)
import Control.SetFunctions (set1, sortValues)

data Tree = Leaf | Branch Int Tree Tree deriving Eq
data Record = Record { count :: Int, label :: String } deriving Eq
data Op = (:*:) Int Bool deriving Eq

prefixes :: [String]
prefixes = ["ReadLegacy", "Prelude"]

samples :: [String]
samples =
  [ showTerm (0 :: Int)
  , showTerm (-42 :: Int)
  , showTerm (123456789012345678901234567890 :: Int)
  , showTerm (1.25 :: Float)
  , showTerm (-2.5 :: Float)
  , showTerm (1.0e-20 :: Float)
  , showTerm (1.0e20 :: Float)
  , showTerm (-0.0 :: Float)
  , showTerm (map chr [0,1,7,8,9,10,11,12,13,31,127,228])
  , showTerm '\''
  , showTerm '"'
  , showTerm '\\'
  , showTerm "a\"b\\c\n"
  , showTerm ([] :: [Int])
  , showTerm [[1,2],[],[3 :: Int]]
  , showTerm ()
  , showTerm (1 :: Int,True)
  , showTerm (1 :: Int,False,'x')
  , showTerm (1 :: Int,2 :: Int,3 :: Int,4 :: Int)
  , showTerm Leaf
  , showTerm (Branch (-3) Leaf (Branch 4 Leaf Leaf))
  , showTerm (Record 7 "record")
  , showTerm (Just [(1 :: Int,True),(2,False)])
  , showTerm (3 :*: True)
  ]

roundTrips :: [String] -> Bool
roundTrips ss = and
  [ readUnqualifiedTerm prefixes (ss !! 0) == (0 :: Int)
  , readUnqualifiedTerm prefixes (ss !! 1) == (-42 :: Int)
  , readUnqualifiedTerm prefixes (ss !! 2) == (123456789012345678901234567890 :: Int)
  , readUnqualifiedTerm prefixes (ss !! 3) == (1.25 :: Float)
  , readUnqualifiedTerm prefixes (ss !! 4) == (-2.5 :: Float)
  , readUnqualifiedTerm prefixes (ss !! 5) == (1.0e-20 :: Float)
  , readUnqualifiedTerm prefixes (ss !! 6) == (1.0e20 :: Float)
  , readUnqualifiedTerm prefixes (ss !! 7) == (-0.0 :: Float)
  , readUnqualifiedTerm prefixes (ss !! 8) == map chr [0,1,7,8,9,10,11,12,13,31,127,228]
  , readUnqualifiedTerm prefixes (ss !! 9) == '\''
  , readUnqualifiedTerm prefixes (ss !! 10) == '"'
  , readUnqualifiedTerm prefixes (ss !! 11) == '\\'
  , readUnqualifiedTerm prefixes (ss !! 12) == "a\"b\\c\n"
  , readUnqualifiedTerm prefixes (ss !! 13) == ([] :: [Int])
  , readUnqualifiedTerm prefixes (ss !! 14) == [[1,2],[],[3 :: Int]]
  , readUnqualifiedTerm prefixes (ss !! 15) == ()
  , readUnqualifiedTerm prefixes (ss !! 16) == (1 :: Int,True)
  , readUnqualifiedTerm prefixes (ss !! 17) == (1 :: Int,False,'x')
  , readUnqualifiedTerm prefixes (ss !! 18) == (1 :: Int,2 :: Int,3 :: Int,4 :: Int)
  , readUnqualifiedTerm prefixes (ss !! 19) == Leaf
  , readUnqualifiedTerm prefixes (ss !! 20) == Branch (-3) Leaf (Branch 4 Leaf Leaf)
  , readUnqualifiedTerm prefixes (ss !! 21) == Record 7 "record"
  , readUnqualifiedTerm prefixes (ss !! 22) == Just [(1 :: Int,True),(2,False)]
  , readUnqualifiedTerm prefixes (ss !! 23) == (3 :*: True)
  ]

readInt :: String -> [(Int,String)]
readInt = readsUnqualifiedTerm prefixes
readTree :: [String] -> String -> [(Tree,String)]
readTree = readsUnqualifiedTerm

validTree :: Bool
validTree = readsUnqualifiedTerm ["ReadLegacy"] "Leaf" == [(Leaf,"")]

charCodes :: [Int]
charCodes = [0..32] ++ [34,39,92,126,127,228,955,128512]
charSamples :: [String]
charSamples = map showTerm (map chr charCodes)
charRoundTrips :: [String] -> Bool
charRoundTrips ss = map (readUnqualifiedTerm prefixes) ss == map chr charCodes

setStrings :: [String]
setStrings = sortValues (set1 id "a\"b\\c\n")
setTailStrings :: [String]
setTailStrings = sortValues (set1 tail "xa\"b\\c\n")

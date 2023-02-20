{-# OPTIONS_CYMAKE -F --pgmF=currypp --optF=defaultrules #-}
{-# OPTIONS_CYMAKE -Wnone #-} -- no warnings

-- From the Curry tutorial
-- Version Fri Jul 15 12:45:38 PDT 2016
-- Determine whether a poker hand scores a four-of-a-kind

import Control.SetFunctions

-------- the cards --------

data Suit = Club | Spade | Heart | Diamond
 deriving Eq

data Rank = Ace | King | Queen | Jack | Ten | Nine | Eight
          | Seven | Six | Five | Four | Three | Two
 deriving (Show,Eq)

data Card = Card Rank Suit
 deriving Eq

rank (Card r _) = r

-------- find whether a hand scores four of a kind --------

isFour (x++[_]++z) | map rank (x++z) == [r,r,r,r] = Just r where r free
isFour'default _ = Nothing

main = (isFour testYes, isFour testNo)

-------- properties --------

testYes = [(Card Six Club),(Card Six Spade),(Card Five Heart),
           (Card Six Heart),(Card Six Diamond)]
testNo  = [(Card Six Club),(Card Ace Spade),(Card Five Heart),
           (Card Ace Club),(Card Six Diamond)]

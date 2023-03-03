{-# OPTIONS_CYMAKE -F --pgmF=currypp --optF=defaultrules #-}
{-# OPTIONS_CYMAKE -Wnone #-} -- no warnings

-- From the Curry tutorial
-- Version Fri Jul 15 12:45:38 PDT 2016
-- Determine whether a poker hand scores a four-of-a-kind

import Control.SetFunctions

-------- the cards --------

data Card = Card Rank Suit deriving Eq
data Rank = Ace | King | Queen | Jack | Ten | Nine | Eight
          | Seven | Six | Five | Four | Three | Two
     deriving (Show,Eq)
data Suit = Club | Spade | Heart | Diamond deriving Eq

rank (Card r _) = r
anyRank :: Rank
anyRank = x where x free

-------- find whether a hand scores four of a kind --------

isFour (x++[_]++z) | map rank (x++z) == [r,r,r,r] = Just r where r free
isFour'default _ = Nothing

-- hands = r1 /= r2 &> [(Card Ace Club),(Card Ace Spade),(Card r3 Heart)
--                     ,(Card r1 Diamond),(Card r2 Diamond)]
--    where r1,r2,r3 free
hands = [(Card anyRank Club),(Card anyRank Spade),(Card anyRank Heart)
        ,(Card anyRank Diamond),(Card anyRank Diamond)]
goal = isFour hands
ord _ _ = EQ
main = minValueBy ord (set0 goal)

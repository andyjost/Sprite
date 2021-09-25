-------------------------------------------------------------------------
-- Example for the use of set functions as described in the paper

-- Sergio Antoy, Michael Hanus:
-- Set Functions for Functional Logic Programming
-- Proc. 11th International ACM SIGPLAN Conference on Principles and Practice
-- of Declarative Programming (PPDP'09), pp. 73-82, 2009

import Control.SetFunctions

-------------------------------------------------------------------------
-- Example: compute a flight itinerary between two cities

-- The cities:
data City = Portland | Frankfurt | Amsterdam | Hamburg

-- The flight numbers:
data FlightNumber = LH469 | NWA92 | LH10 | KL1783
 deriving (Eq,Ord)

(:.) :: Int -> Int -> (Int,Int)
x :. y = (x,y)

-- The flights and their durations:
flight :: (FlightNumber, City, City, (Int,Int))
flight = (LH469, Portland, Frankfurt,10:.15)
flight = (NWA92, Portland, Amsterdam,10:.00)
flight = (LH10,  Frankfurt,Hamburg,   1:.00)
flight = (KL1783,Amsterdam,Hamburg,   1:.52)

-- We consider itineraries with at most one intermediate stop:
itinerary :: City -> City -> [FlightNumber]
itinerary orig dest
   | flight =:= (num,orig,dest,len)
   = [num]
   where num, len free
itinerary orig dest
   | flight =:= (num1,orig,x,len1)
   & flight =:= (num2,x,dest,len2)
   = [num1,num2]
   where num1, len1, num2, len2, x free

duration :: [FlightNumber] -> Int
duration = foldr (+) 0 . map flightToMinutes

flightToMinutes :: FlightNumber -> Int
flightToMinutes fnum | flight =:= (fnum,unknown,unknown,h:.m)
                     = h*60+m
  where h,m free

-- Returns an itinerary with a shortest flight time.
-- Purely declarative specification: an itinerary is the shortest if there is
-- no shorter itinerary.
shortestItin :: City -> City -> [FlightNumber]
shortestItin s e
   | isEmpty (set1 shorterItinThan (duration it))
   = it
   where it = itinerary s e
         shorterItinThan itduration
            | duration its < itduration
            = its
            where its = itinerary s e

goal1 = shortestItin Portland Hamburg   --> [LH469,LH10]


-- Returns an itinerary with a shortest flight time.
-- Implemented by selecting the shortest path from all pathes.
shortestItinSelect :: City -> City -> [FlightNumber]
shortestItinSelect s e
   = minValueBy shorter (set2 itinerary s e)
   where shorter it1 it2 = compare (duration it1) (duration it2)


goal2 = shortestItinSelect Portland Hamburg  --> [LH469,LH10]

-- main = goal1

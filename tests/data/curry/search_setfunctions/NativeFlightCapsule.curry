-- Native capsule reproducer of the base 3.4.0 flight example.
module NativeFlightCapsule where
import Control.SetFunctions

data FlightNumber = LH469 | NWA92 | LH10 | KL1783
 deriving (Eq,Show)

data City = Portland | Frankfurt | Amsterdam | Hamburg

(:.) :: Int -> Int -> (Int,Int)
x :. y = (x,y)

flight :: (FlightNumber,City,City,(Int,Int))
flight = (LH469, Portland, Frankfurt,10:.15)
flight = (NWA92, Portland, Amsterdam,10:.00)
flight = (LH10,  Frankfurt,Hamburg,   1:.00)
flight = (KL1783,Amsterdam,Hamburg,   1:.52)

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
  | isEmpty (set3 shorterItinThan s e (duration it))
  = it
 where it = itinerary s e

shorterItinThan :: City -> City -> Int -> [FlightNumber]
shorterItinThan start end itduration
  | duration its < itduration
  = its
 where its = itinerary start end


main :: [FlightNumber]
main = shortestItin Portland Hamburg

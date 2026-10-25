
main :: IO ()
main = do
  x
  where x = return ()

other :: Int -> Int
other f = case f of
  _ -> x
  where x = 1

import CLPFD

main  | domain colors 0 4 & allDifferent colors
      & domain nation 0 4 & allDifferent nation
      & domain pets   0 4 & allDifferent pets
      & domain drinks 0 4 & allDifferent drinks
      & domain cars   0 4 & allDifferent cars
      & england =# red
      & spain =# dog
      & green =# coffee
      & ukraine =# tea
      & green =# white +# 1
      & bmw =# snake
      & yellow =# toyota
      & milk =# 2
      & norway =# 0
      & ford `nextTo` fox
      & toyota `nextTo` horse
      & honda =# orange
      & japan =# mitsubishi
      & norway `nextTo` blue
      & labeling [] (colors ++ nation ++ pets ++ drinks ++ cars)
      = (owner !! indexOf zebra nation, owner !! indexOf water nation)
  where
    colors@[red, green, white, yellow, blue] = unknown
    nation@[england, spain, ukraine, norway, japan] = unknown
    pets@[dog, snake, fox, horse, zebra] = unknown
    drinks@[coffee, tea, milk, orange, water] = unknown
    cars@[bmw, toyota, ford, honda, mitsubishi] = unknown
    owner = ["england", "spain", "ukraine", "norway", "japan"]

nextTo :: Int -> Int -> Success
nextTo x y = x +# 1 =# y
nextTo x y = x -# 1 =# y

indexOf :: a -> [a] -> Int
indexOf x (y:ys) | x == y    = 0
                 | otherwise = 1 + indexOf x ys

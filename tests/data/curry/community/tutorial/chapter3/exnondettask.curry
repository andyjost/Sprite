data Task = Cut | Polish

data Worker =  Alex | Bert | Chuck
 deriving Eq -- to compare workers

assign :: Task -> Worker
assign Cut    = Alex
assign Cut    = Bert
assign Polish = Bert
assign Polish = Chuck

team :: (Worker, Worker)
team | x /= y = (x,y)
  where x = assign Cut 
        y = assign Polish


main :: (Worker, Worker)
main = team

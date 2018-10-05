xor True x = not x
xor False x = x
test = x=:=True &> ((x=:=y &> a) ? a)
    where a = id y
          x,y free

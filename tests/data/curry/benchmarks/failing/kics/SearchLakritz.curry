import CLPFD

main | domain [h] 1 9 & domain [c] 0 9 & (864 *# x) =# (10000 *# h +# 1230 +# c)
     & labeling [] [x,h,c]
     = x where x, h, c free

f True x = if x then True else False
f False x = if x then False else True
main = f True True

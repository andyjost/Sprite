flip = True ? False

main :: (Bool, Bool)
main = let x=flip in (x, x)

mainalt :: (Bool, Bool)
mainalt = (flip, flip)

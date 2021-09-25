import Control.SetFunctions
f a = [a, True ? False]
main = sortValues $ set1 f (False ? True)

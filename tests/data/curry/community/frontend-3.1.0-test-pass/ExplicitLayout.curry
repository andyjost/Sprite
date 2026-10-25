module ExplicitLayout where
{ f x = let { y = 1; z = 2 } in x + y + z
; g x = case x of { True -> False; False -> True }
; h x = do { y <- return x; return y }
}

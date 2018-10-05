listgen len | len == 0 = []
            | otherwise = x: listgen (len - 1) where x free
main = do
    digit <- getLine
    let n = ord (head digit) - ord '0'
    return $ foldr (&&) True (listgen n)

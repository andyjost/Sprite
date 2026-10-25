import Data.Char

data Term = Term String [Term]

parseTerm :: String -> Term
parseTerm (fun++"("++args++")") | all isAlpha fun = Term fun (parseArgs args)
parseTerm s | all isAlpha s = Term s []

parseArgs :: String -> [Term]
parseArgs (term++","++terms) = parseTerm term : parseArgs terms
parseArgs s = [parseTerm s]

main1 = parseTerm "f(g(a,b))"
-- => Term "f" [Term "g" [Term "a" [],Term "b" []]]
main2 = parseTerm "zero"
-- => Term "zero" []

main = main1

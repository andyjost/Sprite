-- Cryptarithmetic puzzle implemented with Distinct Choices
-- Sergio Antoy & Michael Hanus
-- Wed Feb 19 19:31:58 PST 2003
-- Updated Mon Apr 18 09:03:37 PDT 2011
-- Updated Wed Jun 28 13:29:49 PDT 2017

-- This program finishes instantly in PAKCS (which has residuation) but
-- exhausts all memory in KICS2 (which does not). -- AJ

{-

    A cryptarithmetic puzzle presents an arithmetic computation
    in which digits are replaced by letters.
    The puzzle implemented by this program is:

            SEND+MORE=MONEY

    The problem is to find a correspondence from letters to digits
    that satisfies the computation.
    Different letters stand for different digits and leading zeros
    are disallowed in the encrypted representation of numbers.
    The solution of this puzzle is:

            9567+1085=10652

    This implementation uses the Concurrent Distinct Choices pattern.

-}


main
  | equations
  = {- putStrLn -} ("\n" ++
    " "     ++ show vs ++ show ve ++ show vn ++ show vd ++ "\n" ++
    " "     ++ show vm ++ show vo ++ show vr ++ show ve ++ "\n" ++
    show vm ++ show vo ++ show vn ++ show ve ++ show vy ++ "\n")
  where
      store = [_,_,_,_,_,_,_,_,_,_]

      -- the digits
      vs,ve,vn,vd,vm,vo,vr,vy free

      -- the carries
      c0 = 0 ? 1
      c1 = 0 ? 1
      c2 = 0 ? 1
      c3 = 0 ? 1

      -- the problem's relations, fragmentation is good
      equations   = c3 == vm &
              vs+vm+c2 == c3*10+vo &
              ve+vo+c1 == c2*10+vn &
              vn+vr+c0 == c1*10+ve &
              vd+ve    == c0*10+vy &
              vm == nzdigit 'M' &
              vs == nzdigit 'S' &
              vo == digit   'O' &
              ve == digit   'E' &
              vn == digit   'N' &
              vr == digit   'R' &
              vd == digit   'D' &
              vy == digit   'Y'

      nzdigit token | store !! x == token = x
          where x = 1 ? 2 ? 3 ? 4 ? 5 ? 6 ? 7 ? 8 ? 9

      digit token | store !! x == token = x
          where x = 0 ? 1 ? 2 ? 3 ? 4 ? 5 ? 6 ? 7 ? 8 ? 9

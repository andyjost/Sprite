------------------------------------------------------------------------------
--- The library provides some operations to format values of basic
--- data types with arbitrary flags similarly to the `printf` statement of C.
---
--- These operations are used for the translation of integrated
--- code with the format tag to replace the format specifiers.
---
--- This library follows the C specification for the formatting. This
--- specification may be found at
--- <http://pubs.opengroup.org/onlinepubs/009695399/functions/fprintf.html>
---
--- @author Jasper Sikorra - jsi@informatik.uni-kiel.de
--- @version November 2017
--- @category general
------------------------------------------------------------------------------
module Data.Format
  ( showChar, showInt, showFloat, showString )
 where

import Char
import Integer
import Float
import List
import ReadNumeric

-- Basic type for show functions
type ShowSpec a = Typ -> Maybe Flag -> Maybe Width -> Maybe Precision
                      -> a -> String
type Typ = Char
type Flag = String
type Width = Int
type Precision = Int

--- The function showChar formats a character
--- @param type - will  be ignored
--- @param flags - a string, everything but the minus char will be ignored
--- @param width - the minimal number of characters to be printed
--- @param precision - will be ignored
--- @param char - The char which should be formatted
--- @return A string containing the formatted character
showChar :: ShowSpec Char
showChar _ mf mw _ c =
  let flags     = convertFlags mf
      width     = convertWidth mw
      minusFlag = getMinusFlag flags
      cToString = [c]
  in if minusFlag then fillWithCharsLeftAlign  width ' ' cToString
                  else fillWithCharsRightAlign width ' ' cToString

--- The function showInt formats an Int
--- @param t - A char setting the way of number representation
--- @param mf - A string containing all flags
--- @param mw - The minimal number of characters to be printed
--- @param mp - The minimal number of numbers to be printed
--- @param i - The Int which should be formatted
--- @return A string containing the formatted Int
showInt :: ShowSpec Int
showInt t mf mw mp i = 
  -- convert to better format
  let flags           = convertFlags mf
      width           = convertWidth mw
      prec            = convertPrecision mp
      precPresent     = maybe False (\_ -> True) mp
      minusFlag       = getMinusFlag flags
      plusFlag        = getPlusFlag  flags
      zeroFlag        = getZeroFlag  flags
      spaceFlag       = getSpaceFlag flags
      hashFlag        = getHashFlag  flags
      -- convert to the right numeric system
      iToString       = case t of
                          'i' -> consistentShowInt i
                          'd' -> consistentShowInt i
                          'o' -> showIntAsOct i
                          'x' -> showIntAsHex i
                          'X' -> map toUpper (showIntAsHex i)
      isPositive      = head iToString /= '-'
      isSigned        = (||) (t == 'i') (t == 'd')
      iToStringPosi   = if isPositive then iToString else (tail iToString)
      -- apply precision
      applyPrecision  = fillWithCharsRightAlign prec '0' iToStringPosi
      afterPrecision  = if isPositive then applyPrecision
                                      else '-':applyPrecision
      -- apply flags
      afterPlusFlag   = if (plusFlag && isSigned && isPositive)
                          then '+':afterPrecision
                          else afterPrecision
      afterHashFlag   = if (not (isSigned) && hashFlag && i /= 0)
                          then case t of
                                'o' -> '0'    :afterPlusFlag
                                'x' -> '0':'x':afterPlusFlag
                                'X' -> '0':'X':afterPlusFlag
                          else afterPlusFlag
      afterSpaceFlag  = if (spaceFlag && isSigned && isPositive && not plusFlag)
                          then ' ':afterHashFlag
                          else afterHashFlag
      -- apply width
      afterWidth      = if minusFlag
                          then fillWithCharsLeftAlign width ' ' afterSpaceFlag
                        else let filler = if (zeroFlag && not (precPresent))
                                            then '0' else ' '
                             in fillWithCharsRightAlign width filler
                                  afterSpaceFlag
  -- result
  in afterWidth

--- The function showFloat formats a Float
--- @param t - A char setting wether to use an exponent or not
--- @param mf - A string containing all flags
--- @param mw - The minimal number of characters to be printed before the point
--- @param mp - The exact amount of numbers to be printed after the point
--- @param x - The Float which should be formatted
--- @return A string containing the formatted float
showFloat :: ShowSpec Float
showFloat t mf mw mp x =
  -- convert to better format
  let flags     = convertFlags mf
      width     = convertWidth mw
      prec      = convertPrecision mp
      minusFlag = getMinusFlag flags
      plusFlag  = getPlusFlag flags
      zeroFlag  = getZeroFlag flags
      spaceFlag = getSpaceFlag flags
      hashFlag  = getHashFlag flags
      isPositive = (>=) x 0
      -- Convert to Floater format for easier formatting
      floa      = floatToFloater x
      -- apply type
      afterType = case t of
                    'f' -> eliminateExponent floa
                    'e' -> onePrePoint floa
                    'E' -> onePrePoint floa
      -- apply precision
      afterPrec = roundFloater prec afterType
      -- apply flags
      afterPlusFlag = if (plusFlag && x >= 0)
                        then setMantissaBeforePoint afterPrec
                              ('+':getMantissaBeforePoint afterPrec)
                        else afterPrec
      afterHashFlag = if (not (isPrefixOf (getMantissaAfterPoint afterPlusFlag)
                                          (repeat '0')) || hashFlag || prec > 0)
                        then setMantissaAfterPoint afterPlusFlag
                              ('.':getMantissaAfterPoint afterPlusFlag)
                        else afterPlusFlag
      afterSpaceFlag = if (spaceFlag && not plusFlag && isPositive)
                        then setMantissaBeforePoint afterHashFlag
                              (' ':getMantissaBeforePoint afterHashFlag)
                        else if (not isPositive)
                              then setMantissaBeforePoint afterHashFlag
                                    ('-':getMantissaBeforePoint afterHashFlag)
                              else afterHashFlag
      -- convert back from floater data type
      unitedFloater = case t of
                        'f' -> getMantissaBeforePoint afterSpaceFlag
                                ++ getMantissaAfterPoint afterSpaceFlag
                        'e' -> getMantissaBeforePoint afterSpaceFlag
                                ++ getMantissaAfterPoint afterSpaceFlag
                                ++ "e" ++ showExponent afterSpaceFlag
                        'E' -> getMantissaBeforePoint afterSpaceFlag
                                ++ getMantissaAfterPoint afterSpaceFlag
                                ++ "E" ++ showExponent afterSpaceFlag
      -- apply width
      afterWidth = if minusFlag
                    then fillWithCharsLeftAlign width ' ' unitedFloater
                        else let filler = if zeroFlag
                                            then '0' else ' '
                             in fillWithCharsRightAlign width filler
                                  unitedFloater
  -- result
  in afterWidth

--- The function showString formats a String
--- @param t - Ignored
--- @param mf - A string containing all flags
--- @param mw - The minimal number of characters to be printed
--- @param mp - The exact number of characters of the string to be printed
--- @param s - The String which should be formatted
--- @return A string containing the formatted String
showString :: ShowSpec String
showString _ mf mw mp s =
  let flags      = convertFlags mf
      width      = convertWidth mw
      minusFlag  = getMinusFlag flags
      afterPrec  = maybe s (flip take s) mp
      afterWidth = if minusFlag
                    then fillWithCharsLeftAlign width ' ' afterPrec
                    else fillWithCharsRightAlign width ' ' afterPrec
  in afterWidth

--- FLOATER DATA TYPE BEGIN ----------------------
-- Our own datatype for floats, to make manipulating their string representation
-- easier
data Floater = Floater Sign
                       MantissaBeforePoint
                       MantissaAfterPoint
                       Exponent
data Sign = Positive | Negative
type MantissaBeforePoint = String
type MantissaAfterPoint  = String
type Mantissa            = String
type MantissaSigned      = String
type Exponent = Int

floater :: Sign -> MantissaBeforePoint -> MantissaAfterPoint -> Exponent
  -> Floater
floater = Floater

floaterCreator :: MantissaSigned -> Exponent -> Floater
floaterCreator ms e = setExponent (setMantissaSigned zeroFloater ms) e                        

zeroFloater :: Floater
zeroFloater = Floater Positive "0" "" 0

floatToFloater :: Float -> Floater
floatToFloater f = let (mantissa,exp) = break ((==) 'e') (consistentShowFloat f)
                   in if (exp == "") then floaterCreator mantissa 0
                        else floaterCreator mantissa
                              (maybe failed fst (readInt (tail exp)))

getSign :: Floater -> Sign
getSign (Floater s _ _ _) = s

setSign :: Floater -> Sign -> Floater
setSign (Floater _ m1 m2 e) s = Floater s m1 m2 e

getMantissaBeforePoint :: Floater -> MantissaBeforePoint
getMantissaBeforePoint (Floater _ m1 _ _) = m1

setMantissaBeforePoint :: Floater -> MantissaBeforePoint -> Floater
setMantissaBeforePoint (Floater s _ m2 e) m1 = Floater s m1 m2 e 

getMantissaAfterPoint :: Floater -> MantissaAfterPoint
getMantissaAfterPoint (Floater _ _ m2 _) = m2

setMantissaAfterPoint :: Floater -> MantissaAfterPoint -> Floater
setMantissaAfterPoint (Floater s m1 _ e) m2 = Floater s m1 m2 e

getMantissa :: Floater -> Mantissa
getMantissa (Floater _ m1 m2 _) = m1 ++ ('.':m2)

setMantissa :: Floater -> Mantissa -> Floater
setMantissa (Floater s _ _ e) m = let (bP,aP) = break ((==) '.') m
                                  in Floater s bP (tail aP) e

setMantissaSigned :: Floater -> MantissaSigned -> Floater
setMantissaSigned (Floater _ _ _ e) m =
  let (bP,aP) = break ((==) '.') m
  in  if (head bP == '-') then
          Floater Negative (tail bP) (tail aP) e
        else Floater Positive bP (tail aP) e

getExponent :: Floater -> Exponent
getExponent (Floater _ _ _ e) = e

setExponent :: Floater -> Exponent -> Floater
setExponent (Floater s m1 m2 _) e = Floater s m1 m2 e

showExponent :: Floater -> String
showExponent (Floater _ _ _ e) = let st = consistentShowInt e
                                 in  if      (e < -10) then st
                                     else if (e < 0  ) then ('-':'0':tail st)
                                     else if (e < 10 ) then ('+':'0':st)
                                     else                   ('+':st)

eliminateExponent :: Floater -> Floater
eliminateExponent (Floater s m1 m2 e) | e == 0 = Floater s m1 m2 e
                                      | e >  0 =
  if (null m2) then eliminateExponent (Floater s (m1 ++ "0") "" (e-1))
               else eliminateExponent
                      (Floater s (m1 ++ [(head m2)]) (tail m2) (e-1))
                                      | e <  0 =
  if (null m1) then eliminateExponent (Floater s "" ("0" ++ m2) (e+1))
               else eliminateExponent (Floater s (init m1) ([last m1] ++ m2)
                                              (e+1))

onePrePoint :: Floater -> Floater
onePrePoint (Floater s m1 m2 e) | m1 == "0" && m2 == ""       =
  Floater s m1 m2 e
                                | m1 == "0" && m2 /= ""       =
  onePrePoint (Floater s [head m2] (tail m2) (e-1))
                                | m1 /= "0" && length m1 == 1 =
  Floater s m1 m2 e
                                | m1 /= "0" && length m1 >= 1 =
  onePrePoint (Floater s (init m1) ((last m1):m2) (e+1))

roundFloater :: Int -> Floater -> Floater
roundFloater n (Floater s m1 m2 e) =
    if (length m2 <= n)
      then Floater s m1 (m2 ++ replicate (n - length m2) '0') e
      else
        if (digitToInt (m2 !! n) < 5)
          then Floater s m1 (take n m2) e
          else roundUp (Floater s m1 (take n m2) e)
  where
    roundUp :: Floater -> Floater
    roundUp (Floater s m1 m2 e) = Floater s m1Result m2Result e
      where
        (m2Result,  m2Overflow) = roundStringUp m2
        (m1Rounded, m1Overflow) = if m2Overflow
                                    then roundStringUp m1
                                    else (m1, False)
        m1Result = if m1Overflow
                     then "1" ++ m1Rounded
                     else m1Rounded
    roundStringUp :: String -> (String, Bool)
    roundStringUp s = let (res, overflow) = roundBigEndianStrUp (reverse s) True
                      in (reverse res, overflow)

    roundBigEndianStrUp :: String -> Bool -> (String, Bool)
    roundBigEndianStrUp ""     b     = ("", b)
    roundBigEndianStrUp (c:cs) False = (c:cs, False)
    roundBigEndianStrUp (c:cs) True  = let n = digitToInt c
                                       in if n == 9
                                            then
                                              let (rs, overflow) = roundBigEndianStrUp cs True
                                              in  ('0':rs, overflow)
                                            else (show (n+1) ++ cs, False)

--- FLOATER DATA TYPE END ------------------------

--- HANDLING OF FLAGS BEGIN ----------------------
-- | Handling flags
data Flags = Flags Bool     -- '-' appears
                   Bool     -- '+' appears
                   Bool     -- '0' appears
                   Bool     -- ' ' appears
                   Bool     -- '#' appears

getMinusFlag :: Flags -> Bool
getMinusFlag (Flags b _ _ _ _) = b

getPlusFlag :: Flags -> Bool
getPlusFlag (Flags _ b _ _ _)  = b

getZeroFlag :: Flags -> Bool
getZeroFlag (Flags _ _ b _ _)  = b

getSpaceFlag :: Flags -> Bool
getSpaceFlag (Flags _ _ _ b _) = b

getHashFlag :: Flags -> Bool
getHashFlag (Flags _ _ _ _ b)  = b

-- Converters of arguments
convertFlags :: Maybe String -> Flags
convertFlags = maybe (Flags False False False False False)
                     (convFlags (Flags False False False False False))
  where
    convFlags :: Flags -> String -> Flags
    convFlags f                      ""     = f
    convFlags (Flags b1 b2 b3 b4 b5) (c:cs) = case c of
      '-' -> convFlags (Flags True b2   b3   b4   b5  ) cs
      '+' -> convFlags (Flags b1   True b3   b4   b5  ) cs
      '0' -> convFlags (Flags b1   b2   True b4   b5  ) cs
      ' ' -> convFlags (Flags b1   b2   b3   True b5  ) cs
      '#' -> convFlags (Flags b1   b2   b3   b4   True) cs

convertWidth :: Maybe Width -> Int
convertWidth = maybe 0 id

convertPrecision :: Maybe Int -> Int
convertPrecision = maybe 1 id

--- HANDLING OF FLAGS END ------------------------

--- FILLING A STRING WITH APPROPRIATE ALIGNMENT
data Alignment = LeftAlign | RightAlign
 deriving Eq

fillWithCharsLeftAlign :: Int -> Char -> String -> String
fillWithCharsLeftAlign  = fillWithChars LeftAlign

fillWithCharsRightAlign :: Int -> Char -> String -> String
fillWithCharsRightAlign = fillWithChars RightAlign

fillWithChars :: Alignment -> Int -> Char -> String -> String
fillWithChars a n c st = let i = n - length st
                         in if (i > 0)
                              then
                                if (a == RightAlign)
                                  then replicate i c ++ st
                                  else st ++ replicate i c
                              else st

--- CONSISTENT NUMBER REPRESENTATION AS A STRING -----------
-- The show function on Int and Float is different for pakcs and kics2.
-- show -1
-- pakcs: (-1)
-- kics2: -1
-- Therefor we need a function that removes the parenthesis.
consistentShowInt :: Int -> String
consistentShowInt = showWithoutParantheses '(' ')' . show

consistentShowFloat :: Float -> String
consistentShowFloat = showWithoutParantheses '(' ')' . show

showWithoutParantheses :: Char -> Char -> String -> String
showWithoutParantheses start_p end_p s =
  let lengthOfString = length s
  in if (lengthOfString >= 2)
      then
        let (h,t) = splitAt 1 s
            (r,l) = splitAt (lengthOfString-2) t
        in if (head h == start_p && head l == end_p)
            then r
            else s
      else s

--- CONVERSION OF INTEGERS TO DIFFERENT NUMERATIVE SYSTEMS -----
showIntAsOct :: Int -> String
showIntAsOct = convertToBase 8

showIntAsHex :: Int -> String
showIntAsHex = convertToBase 16

convertToBase :: Int -> Int -> String
convertToBase b n = 
    if (b < 2 || b > 16)
      then error $ "Can't handle base " ++ (show b)
                   ++ ". Can only handle bases between 2 and 16."
      else if (n < -2147483647)
            then error $ "Can only handle integers geq -2147483648."
      else if (n == 0) then "0"
      else if (n < 0)  then let num = bitNot ((n*(-1))-1) 
                            in  cTB "" b num
      else cTB "" b n
  where
    cTB :: String -> Int -> Int -> String
    cTB acc base m = if (m == 0) then acc else
      let dr = ((div m base),(mod m base))
          d  = (fst dr)
          r  = (snd dr)
          st = if (r < 10) then (show r) else
            case r of
              10 -> "a"
              11 -> "b"
              12 -> "c"
              13 -> "d"
              14 -> "e"
              15 -> "f"
      in cTB (st ++ acc) b d

------------------------------------------------------------------------------

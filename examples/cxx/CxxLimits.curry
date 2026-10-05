-- The fundamental types of C++ and the LP64 data model.
--
-- Data model: LP64, the model of the x86-64 System V ABI (Linux, the BSDs,
-- macOS).  int has 32 bits; long, long long and pointers have 64 bits; char
-- is signed; long double is the 80-bit x87 format stored in 16 bytes.
--
-- Every function of this module is a table over Fund, the fundamental types.
-- The algebra of compound types, the traits and the printer are in CxxType,
-- which imports this module.  A table has no entry where C++ has no value:
-- void has no size, no alignment and no rank; the floating types have no
-- integer range; the maxima of the two 64-bit unsigned types, 2^64 - 1, do
-- not fit the 64-bit Int of the runtime and have no entry either.

module CxxLimits where

-- The fundamental types.  NullptrT is std::nullptr_t.  The wide character
-- types (wchar_t, char8_t, char16_t, char32_t) are not modelled.
data Fund = Void | Bool | Char | SChar | UChar | Short | UShort | Int | UInt
          | Long | ULong | LLong | ULLong | Float | Double | LDouble | NullptrT
  deriving (Eq, Ord, Show)

-- Every fundamental type, in the order of the declaration.
funds :: [Fund]
funds = [ Void, Bool, Char, SChar, UChar, Short, UShort, Int, UInt
        , Long, ULong, LLong, ULLong, Float, Double, LDouble, NullptrT ]

-- The spelling of each type in C++.
spelling :: Fund -> String
spelling Void     = "void"
spelling Bool     = "bool"
spelling Char     = "char"
spelling SChar    = "signed char"
spelling UChar    = "unsigned char"
spelling Short    = "short"
spelling UShort   = "unsigned short"
spelling Int      = "int"
spelling UInt     = "unsigned int"
spelling Long     = "long"
spelling ULong    = "unsigned long"
spelling LLong    = "long long"
spelling ULLong   = "unsigned long long"
spelling Float    = "float"
spelling Double   = "double"
spelling LDouble  = "long double"
spelling NullptrT = "std::nullptr_t"

-- sizeof, in bytes.  void has no size.
sizeofF :: Fund -> Int
sizeofF Bool     = 1
sizeofF Char     = 1
sizeofF SChar    = 1
sizeofF UChar    = 1
sizeofF Short    = 2
sizeofF UShort   = 2
sizeofF Int      = 4
sizeofF UInt     = 4
sizeofF Long     = 8
sizeofF ULong    = 8
sizeofF LLong    = 8
sizeofF ULLong   = 8
sizeofF Float    = 4
sizeofF Double   = 8
sizeofF LDouble  = 16
sizeofF NullptrT = 8

-- alignof, in bytes.  Every fundamental type of this model is aligned to
-- its size.  void has no alignment.
alignofF :: Fund -> Int
alignofF f = sizeofF f

-- std::numeric_limits<T>::digits: the value bits of an integer type, without
-- the sign bit; the mantissa bits of a floating type; 0 for the types that
-- numeric_limits does not specialize.
digits :: Fund -> Int
digits Void     = 0
digits Bool     = 1
digits Char     = 7
digits SChar    = 7
digits UChar    = 8
digits Short    = 15
digits UShort   = 16
digits Int      = 31
digits UInt     = 32
digits Long     = 63
digits ULong    = 64
digits LLong    = 63
digits ULLong   = 64
digits Float    = 24
digits Double   = 53
digits LDouble  = 64
digits NullptrT = 0

-- std::numeric_limits<T>::is_signed.  char is signed in this model.
isSigned :: Fund -> Bool
isSigned Void     = False
isSigned Bool     = False
isSigned Char     = True
isSigned SChar    = True
isSigned UChar    = False
isSigned Short    = True
isSigned UShort   = False
isSigned Int      = True
isSigned UInt     = False
isSigned Long     = True
isSigned ULong    = False
isSigned LLong    = True
isSigned ULLong   = False
isSigned Float    = True
isSigned Double   = True
isSigned LDouble  = True
isSigned NullptrT = False

-- The classes of the arithmetic types.
isIntegral :: Fund -> Bool
isIntegral f = f `elem` [ Bool, Char, SChar, UChar, Short, UShort, Int, UInt
                        , Long, ULong, LLong, ULLong ]

isFloating :: Fund -> Bool
isFloating f = f `elem` [Float, Double, LDouble]

isArithmetic :: Fund -> Bool
isArithmetic f = isIntegral f || isFloating f

-- std::numeric_limits<T>::min and max of the integral types, from the digits
-- and the sign.  The maxima of unsigned long and unsigned long long have no
-- entry (see the module comment); the floating types have no integer range.
minValue :: Fund -> Int
minValue f | isIntegral f = if isSigned f then negate (2 ^ digits f) else 0

maxValue :: Fund -> Int
maxValue f | isIntegral f && digits f < 64 = 2 ^ digits f - 1

-- The conversion rank of an arithmetic type ([conv.rank]).  The integer
-- conversion ranks come first; a signed type and its unsigned counterpart
-- have the same rank.  The floating types rank above every integer type, so
-- that the usual arithmetic conversions can compare any two arithmetic types
-- by rank alone.  void and std::nullptr_t have no rank.
rank :: Fund -> Int
rank Bool    = 0
rank Char    = 1
rank SChar   = 1
rank UChar   = 1
rank Short   = 2
rank UShort  = 2
rank Int     = 3
rank UInt    = 3
rank Long    = 4
rank ULong   = 4
rank LLong   = 5
rank ULLong  = 5
rank Float   = 6
rank Double  = 7
rank LDouble = 8

-- The signed counterpart of an integral type other than bool, as
-- std::make_signed names it.  char becomes signed char.
signedOf :: Fund -> Fund
signedOf Char   = SChar
signedOf SChar  = SChar
signedOf UChar  = SChar
signedOf Short  = Short
signedOf UShort = Short
signedOf Int    = Int
signedOf UInt   = Int
signedOf Long   = Long
signedOf ULong  = Long
signedOf LLong  = LLong
signedOf ULLong = LLong

-- The unsigned counterpart, as std::make_unsigned names it.
unsignedOf :: Fund -> Fund
unsignedOf Char   = UChar
unsignedOf SChar  = UChar
unsignedOf UChar  = UChar
unsignedOf Short  = UShort
unsignedOf UShort = UShort
unsignedOf Int    = UInt
unsignedOf UInt   = UInt
unsignedOf Long   = ULong
unsignedOf ULong  = ULong
unsignedOf LLong  = ULLong
unsignedOf ULLong = ULLong

-- Integral promotion ([conv.prom]) of an integral type.  Under LP64 every
-- integral type narrower than int, and bool, promotes to int; the others
-- stay.  A floating type is not changed by integral promotion.
promoted :: Fund -> Fund
promoted f = if isIntegral f && rank f < rank Int then Int else f

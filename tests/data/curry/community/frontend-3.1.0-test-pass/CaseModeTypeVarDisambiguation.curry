{-# OPTIONS_FRONTEND -c haskell #-}

data X = A | B

-- X is initially parsed as a type variable and first later (in the
-- TypeSyntaxCheck) disambiguated into a constructor type. Same goes for the
-- value-level A and B constructors and the SyntaxCheck. This test is to ensure
-- that the CaseModeCheck happens after the syntax checks and does not wrongly
-- produce a warning (in the default `curry` case mode) here. Note that this
-- uses the Haskell case mode to ensure that it would error otherwise.

f :: X -> X
f A = B
f B = A

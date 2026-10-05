-- Goals without type signatures, for func_goal_defaulting.py (item Y5 of
-- the typed boundary, issue #54).  The front end generalizes each binding
-- with its class constraints, so most goals here take dictionary
-- parameters.  The functional driver reads the number of value parameters
-- from the scheme and runs them.  The PAKCS REPL, the oracle, defaults the
-- constraints as Sprite does.  The comments give the type of each goal.

goal1 = 1 + 2                            -- Num a => a
goal2 = 3 / 2                            -- Fractional a => a
goal3 = fromIntegral 3                   -- Num a => a
goal4 = []                               -- [a]
goal5 = x where x free                   -- Data a => a; defaults to Bool
goal6 = Just 5                           -- Num a => Maybe a
goal7 = show (1 + 2)                     -- [Char]; the front end defaults a
goal8 = (1, 'a')                         -- Num a => (a, Char)
goal9 = 2 ^ 3                            -- Num a => a
goal10 = [1, 2.5]                        -- Fractional a => [a]
goal11 = id                              -- a -> a; a function value
goal12 = x =:= 1 &> True where x free    -- Bool; the front end defaults a
goal13 = 1 ? 2                           -- Num a => a; two values
goal14 = (x, y) where x, y free          -- (Data a, Data b) => (a, b)
goal15 = fmap (+1) (Just 1)              -- Num a => Maybe a
goal16 = take 3 [1 ..]                   -- (Enum a, Num a) => [a]

-- A goal with a value parameter.  The driver skips it.
goal17 n = n + 1                         -- Num a => a -> a

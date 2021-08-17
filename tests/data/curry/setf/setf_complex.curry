import SetFunctions

data Arg = A | B | C
data Result = G_A | G_B | G_C | H_A | H_B | H_C

f = g ? h

g A = G_A
g B = G_B
g C = G_C
h A = H_A
h B = H_B
h C = H_C

apply1 f a b = f a ? f b
apply2 a b = f a ? f b
apply3 f a b = f (a ? b)
apply4 a b = f (a ? b)

arg = A ? B

-- {G_A} ? {G_A, G_B} ? {H_A} ? {H_A, H_B}
goal1a = (set3 apply1) f arg A
goal1b = (set3 apply3) f arg A

-- {G_A, H_A} ? {G_A, G_B, H_A, H_B}
goal2a = (set2 apply2) arg A
goal2b = (set2 apply4) arg A

goal3 = (set3 apply1) g A x where x free

-- {G_A} ? {G_A, G_B} ? {G_A, G_C} ? {G_B} ? {G_B, G_C} ?
-- {H_A} ? {H_A, H_B} ? {H_A, H_C} ? {H_B} ? {H_B, H_C}
-- (?) PAKCS: evaluation suspended.  KiCS2 gives the correct answer.
-- KiCS2:
--     (Values [G_A,G_A])
--     (Values [G_B,G_A])
--     (Values [H_A,H_A])
--     (Values [H_B,H_A])
--     (Values [G_B,G_B])
--     (Values [H_B,H_B])
--     (Values [G_A,G_C])
--     (Values [G_B,G_C])
--     (Values [H_A,H_C])
--     (Values [H_B,H_C])
--     (Values [G_A,G_B]) -- duplicate
--     (Values [H_A,H_B]) -- duplicate
goal4a = (set3 apply1) f arg x where x free
goal4b = (set3 apply3) f arg x where x free


main = (
    allValues $ set1 allValues goal1a
  , allValues $ set1 allValues goal1b
  , allValues $ set1 allValues goal2a
  , allValues $ set1 allValues goal2b
  , allValues $ set1 allValues goal3
  , allValues $ set1 allValues goal4a
  , allValues $ set1 allValues goal4b
  )

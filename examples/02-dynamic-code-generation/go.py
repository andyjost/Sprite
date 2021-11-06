import curry

# Define a module dynamically.
Nat = curry.compile(
'''
data Nat = O | I Nat deriving Show

natToInt :: Nat -> Int
natToInt O = 0
natToInt (I n) = 1 + natToInt n

natFromInt :: Int -> Nat
natFromInt i | i == 0    = O
             | otherwise = I (natFromInt (i-1))
''')

# Build a goal dynamically.
goal = curry.expr(Nat.natToInt, [Nat.I, Nat.O])
print 'goal1:', goal

# Evaluate.
print next(curry.eval(goal))


# Compile a Curry expression dynamically.
goal2 = curry.compile('natFromInt 3', mode='expr', imports=Nat)
print 'goal2:', goal2
print next(curry.eval(goal2))


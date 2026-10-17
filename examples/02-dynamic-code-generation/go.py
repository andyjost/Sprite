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
goal = Nat.natToInt(Nat.I(Nat.O))
print('goal1:', goal)

# Evaluate.
print(curry.eval(goal).one())


# Compile a Curry expression dynamically.
goal2 = curry.parse('natFromInt 3', imports=[Nat])
print('goal2:', goal2)
print(curry.eval(goal2).one())

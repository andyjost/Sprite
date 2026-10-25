--- Non-linearity between functional and other pattern is not handled correctly
--- Redmine - curry-frontend - bug #1226

{-
Nonlinear patterns such as @f x x = x@ should be replaced
by fresh variables and strict equations:

<pre>
f x y | x =:= y = x
</pre>

However, the frontend does not do this when one of the patterns is a
functional pattern. For instance, @g x (id x) = x@ is translated to

<pre>
g x y | id x =:<= y = x
</pre>

Whenever @g@ is called with a free variable as its first argument,
this variable could now be bound to an *expression* and not a constructor term,
which violates the principle that *a free variable represents the set
of all constructor terms*.

Therefore, the nonlinearity must also be replaced by a strict equality:

<pre>
g x y | id z =:<= y &> x =:= z = x
  where z free
</pre>

Note that this does *not account* for multiple variable occurrences
*inside a single functional pattern*.
For example, @h (pair x x) = x@ where @pair x y = (x, y)@
should be translated as:

<pre>
h y | pair x x =:<= y = x where x free
</pre>

This is because nonlinearity inside a single functional pattern is resolved
on demand because the pattern-function may or may not disregard
some of the occurrences of the variable during evaluation.

For nonlinearity between *multiple functional patterns*,
the nonlinearity should be replaced as discussed above:

<pre>
k (id x) (id x) = x
=>
k (id x) (id y) | x =:= y = x
=>
k a b | id x =:<= a &> id y =:<= b &> x =:= y = x
  where x, y free
</pre>
-}

{-# LANGUAGE FunctionalPatterns #-}

f :: Data a => a -> a -> a
f x (id x) = x

-- Expected translation:
-- f x y = let z free in id z =:<= y &> x =:= z &> x

g :: Data a => a -> a -> a
g (id x) (id x) = x

-- Expected translation:
-- g x y = let a, b free in id a =:<= x &> id b =:<= y &> a =:= b &> a

h :: Data a => (a, a) -> a
h (pair x x) = x

-- Expected translation:
-- h y = let x free in pair x x =:<= y &> x

pair :: a -> b -> (a, b)
pair x y = (x, y)

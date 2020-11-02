======
Theory
======

.. toctree::


Free Variable Instantiation
===========================

Free variables are unbound or bound.

..
  SA>
  What does it mean to reuse or share the same generator?  When a generator is
  placed in service, any variable is unbound.  A variable occurring in the
  generator may become bound.  Is this binding ever undo or reconsidered?  If
  it is, do we sat that the generator is still the same?  Below is an example:
  _
  f, g :: Bool -> Int
  f True = 0
  g False = 1
  _
  t :: Int
  t = f x ? g x where x free
  _
  u :: (Int, Int)
  u = (f x, g x) where x free
  _
  Expressions t and u create a generator that is shared by two expressions.
  But the sharing is different.  In t after evaluating f the binding must be
  undone, or refreshed or limited to a fingerprint.  In u, the binding is not
  undone and as a consequence the evaluation of g fails.
  _
  AJ>
  Yes, I agree the situation is different.  To me, "reuse" means that each
  variable, x, constructs its generator, g, at most once.  Then, whenever x is
  needed in a function-rooted context, C, the edge pointing to x in C is
  redirected to g.  To not reuse would mean to create a copy of g for each
  needed occurrence of x.
  _
  (Could you please tell me if this notation is correct?  I always struggle
  with graph replacement:
  _
    [1] Whenever we have function-rooted context C, and expression C[x], where
        x is needed in C, substitute C[x] with C[g]_x.
    [2] Whenever we have a constructor-rooted context D, and expression D[x],
        where x is needed in D, substitute D[x] with D[g]_x iff x is bound.
  )
  _
  The difference is played out in the fingerprint.  Associated with x is an
  identifier, i_x, and at the head of g is a choice labeled with i_x.
  _
  After x is instantiated (i.e., replaced with a generator), the target of the
  replacement (i.e., where x was and where g now is) appears only in C or
  dominators of C.  C[g] appears in one or more contexts.  Note that the
  replacement only occurs in *function-rooted* contexts.
  _
  In contexts where C[g] is NOT needed, instantiation does no harm, because
  the target expression will eventually be discarded.  In contexts where C[g]
  is needed, there are two cases.  First, if x is eventually bound by other
  means, then this replacement does no harm because it would have eventually
  occurred anyway.  Second, if x is never bound then it appears in a
  constructor expression (i.e., it is only needed by constructor symbols, never
  by a function symbol; otherwise it would be bound and the previous case would
  apply).  In this context, the fingerprint cannot contain choice i_x, because
  that choice is only introduced at the head of g, but x was never bound.
  Therefore, we can safely output x unbound.

..
  Implementing =:=
  ----------------
  I think that constraint nodes are the only way to go when implementing =:=.
  We had discussed the following example:
  _
      (x =:= True &> x) ?_1 x
  _
  Our approach was to replace x with a generator in expression 1L based on our
  knowledge (from the fingerprint) that x is bound in that context.  That step
  does not impact 1R, a context in which x is unbound.  That works in the above
  example, because the replacement occurs at the topmost level.  Sprite has a
  “frame” object with fingerprint 1L and expression x – I’ll write it {1L | x}.
  We update the frame, replacing x with some generator of the form (... ? ...),
  and this has no effect on the frame {1R | x}.
  _
  This approach fails when there is more depth, e.g.:
  _
      let fx = f x in (x =:= True &> fx) ? fx
  _
  In this case, our approach would have us perform the following replacement:
  _
      { 1L | f x } -> { 1L | f (… ? …) }
  _
  But since f x is shared, that step has a side-effect in the other frame:
  _
      { 1R | f x } -> { 1R | f (… ? …) }

..
  Implementing =<:=
  -----------------
  Here is an example:
  _
      true True = True
      x =:<= true y &> e ? e where e=not x; x,y free
      _
  After pull-tabbing and evaluating the RHS of &>, the work queue has two
  elements:
  _
      (1) not x   fingerprint=1L, bindings={x->true y; y free}
      (2) not x   fingerprint=1R, bindings={x free}
  _
  The expression “not x” is shared.  In (1), we cannot substitute the binding
  for x because that would also affect (2) causing us to lose the value True.
  What’s needed instead is to replace x with a generator and then filter out
  results that are inconsistent with x =:<= true y.


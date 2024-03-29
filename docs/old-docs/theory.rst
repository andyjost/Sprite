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

..
  Activating lazy bindings.
  I discovered a new detail when binding variables in Sprite.  Let’s use the example from yesterday:
  _
      last (xs++[x]) = x
      main = snd $ last [(failed, True)]
  _
  This eventually comes to the following state:
  _
      snd x   {{x -> (failed, True)}}
  _
  where x has a lazy binding.
  _
  I had said that I always activate lazy bindings by prepending a =:=
  expression.  In this case, Sprite would instantiate x based on the rules of
  snd, and then prepend the binding for x once the choice reaches the top:
  _
      snd ((_a, _b) ?_x failed)     # Instantiate x.  Note, the generator for (,) must begin with a choice.
      snd (_a, _b) ?_x snd failed   # Pull tab
      x =:= (failed, True) &> (snd (_a, _b) ?_x snd failed)     # Activate the lazy binding.
  _
  This does not work because the binding fails.  Instead, what’s needed is to
  bind x’s generator with the expression using =:<=, so the last state should
  be:
  _
      ((a, _b) ?_x failed) =:<= (failed, True) &> (snd (_a, _b) ?_x snd failed)
  _
  This has the effect of interleaving =:<= with normal steps.
  _
  In other cases, it is necessary to use =:=.  Consider the following:
  _
      main = last [f] where f=True
  _
  This time we end up with the value x where x has a lazy binding x->f.  Since
  there is no generator for x, we cannot use the above (I could use the above
  approach if ICurry gave me the type of x).
  _
  In this case, it is safe to use =:= because x is a value, and therefore must
  be reduces to normal form.
  _
  So I have two cases in general.  For free variable x with generator gen(x)
  and lazy binding {x->e}:
  _
    [1] When x is narrowed, apply (gen(x) =:<= e &>) to the top-level
        expression.
    [2] When x’s normal form is needed apply (x =:= e &>) to the top-level
        expression.
  _
  (In both cases delete the lazy binding.)


..
  > All OK, but how does a "lazy" binding differ from a "normal" binding?
  A lazy binding is conceptually equivalent to a normal binding (they must have
  the same effect or the semantics would change).  Consider "x =:<= f," which
  binds f to x.
  _
  In a backtracking implementation, this can be implemented by redirecting x to
  f.  If x is needed, then at some point in the future, an occurrence of x will
  be handled by reducing f.
  _
  In Sprite, x cannot be redirected to f.  This is because Sprite does graph
  rewriting with maximal sharing, and so x can occur in several contexts,
  potentially including some in which x is not bound to f.  Instead of
  redirecting, Sprite makes note of the binding in (or alongside) the
  fingerprint.   If x is needed in the future, it is replaced with a generator.
  If a choice originating from x's generator reaches the root, then we know x
  has been reduced.  That is an indication to inspect the lazy binding.  Since
  x has a binding to f, Sprite now evaluates f and filters out values that are
  not consistent.
  _
  Example:
  _
  	f = True
  	main = (x =:<= f) &> x
  _
  Backtracking implementation:
  	1. Redirect x to f
  	2. Evaluate f
  	3. Yield True
  _
  Sprite implementation:
  	1. Add (x -> f) to the fingerprint.
  	2. Evaluate x
  	3. Replace x with True ?_x False.  The expression is choice-rooted.
    4. To remove ?_x from the top, check for a lazy binding.  x has the binding
       f.  Evaluate f, producing True.
  	5. Choose the left branch of ?_x, because x is True.
  	6. Yield True
  _
  > The expressions (x ? failed) and x should be the same in every context.
  > I am missing something here.
  Perhaps.  Sprite uses the choice as a signal to check for lazy bindings.
  When variable x_i is replaced with a generator, that generator must begin
  with choice ?_i.  Choice ?_i arriving at the root of an expression is the
  signal for Sprite to check for lazy bindings for x_i.  For unary types, T = A
  ys, to get a choice into the generator root, the generator is written as "A
  ys ? failed."
  _
  _
  > When you say "x is a value" you must mean something else. x is a variable,
  > may be eventually bound to a value.  How can we know in advance?
	In the Fair Scheme, constructors are handled through recursive calls to the N
  routine.  Functions are handled by recursive calls to the S routine.  The
  computation state at any time is N*S*, i.e., zero or more calls to N followed
  by zero or more calls to S.  If a free variable is handled by N, then it is
  definitely part of a value (because there are no intervening function symbols).
  When x is *definitely* a value, it is safe to use =:= to effectuate its
  binding.
  _
  A free variable has three possible destinies:
  _
  	1. It is not needed; hence, it is discarded.
    2. It is needed in some function-rooted context.  We narrow by replacing it
       with a generator and then pull-tabbing.
    3. It is needed only in constructor-rooted contexts.
  _
  I am targeting case #3.  In that case, if the variable occurs in a lazy
  binding, (x -> e), then Sprite uses x =:= e to effectuate the binding.


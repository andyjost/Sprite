'''
Free variables and choices made from Python: issue #33, item Y1 of the typed
boundary (#50).  ``curry.free()`` is one shared node per marker, a call of
``Prelude.unknown``, so the runtime creates the variable with a fresh id;
``curry.choice`` is a call of ``Prelude.?``; and ``RuntimeState.set_goal``
registers the free variables a goal already holds, behind a counter of the
free variables made outside an evaluation.  So a marker reused in a second
goal, a goal that came out of ``compile(mode='expr')``, and a cyclic goal
that holds a marker evaluate on both backends.  A marker inside a lazy
iterator, a value of an earlier evaluation that holds a free variable, and a
marker used after ``curry.reset`` evaluate too.  ``raw_expr`` keeps the raw
``Free`` and ``Choice`` nodes, which unit_expr.py pins.
'''
import cytest # from ./lib; must be first
from curry.backends.generic.eval import evaluator
from curry.expressions import anchor, choice, cons, free, ref
from curry import inspect
import curry

def values(*args):
  '''The values of a goal as Python objects, in order.'''
  return list(curry.eval(*args, converter='topython'))

def interpreter_state():
  interp = curry.getInterpreter()
  return interp.backend.get_interpreter_state(interp)

def create_variable(marker):
  '''
  Evaluates ``id marker`` once, so that the node of the marker is a free
  variable with a fresh id (the step of ``unknown`` forwarded it), and
  returns that node.  The variable is created, not narrowed: it has no
  generator and no binding.
  '''
  P = curry.import_('Prelude')
  value, = curry.eval(P.id, marker)
  node = inspect.fwd_chain_target(curry.expr(marker))
  assert inspect.isa_freevar(node)
  return node

class TestFreeMarkers(cytest.TestCase):
  '''``curry.free`` through ``curry.expr`` and ``curry.eval``.'''

  def test_issue33_goal(self):
    '''The goal of #33, xs ++ [3] =:= [1,2,3] &> xs, gives [1, 2].'''
    P = curry.import_('Prelude')
    xs = curry.free()
    goal = curry.expr(
        P.cond
      , curry.expr(P.constrEq, curry.expr(getattr(P, '++'), xs, [3]), [1, 2, 3])
      , xs
      )
    self.assertEqual(values(goal), [[1, 2]])

  def test_two_markers(self):
    '''Two markers are two variables: constrEq (x, y) (1, 2) gives True.'''
    P = curry.import_('Prelude')
    x, y = curry.free(), curry.free()
    self.assertEqual(values(P.constrEq, (x, y), (1, 2)), [True])

  def test_one_node_per_marker(self):
    '''
    One marker is one node, a call of Prelude.unknown, in one expression and
    across expressions.  Two markers are two nodes.
    '''
    P = curry.import_('Prelude')
    x, y = curry.free(), curry.free()
    e = curry.expr((x, x, y))
    first, second, third = e[0], e[1], e[2]
    self.assertIs(first, second)
    self.assertIsNot(first, third)
    self.assertIs(curry.expr(x), first)
    self.assertEqual(first.info.name, P.unknown.info.name)
    self.assertRegex(str(first), r'^unknown ')

  def test_marker_reuse(self):
    '''
    A marker evaluated once is a free variable.  The same marker in a second
    goal is the same variable, registered with the second evaluation.  The
    issue spells the second goal ``x =:= 1``; ``=:=`` takes its ``Data``
    dictionary first, so the test passes the dictionary of ``Int`` and also
    uses ``constrEq``, which takes none.
    '''
    P = curry.import_('Prelude')
    x = curry.free()
    value, = curry.eval(P.id, x)
    self.assertIsaFreevar(value)
    self.assertEqual(str(value), '_a')
    self.assertEqual(values(P.constrEq, x, 1), [True])
    y = curry.free()
    value, = curry.eval(P.id, y)
    self.assertEqual(str(value), '_a')
    dictionary = curry.symbol('Prelude._inst#Prelude.Data#Prelude.Int')
    self.assertEqual(values(getattr(P, '=:='), dictionary, y, 1), [True])

  def test_goal_evaluated_twice(self):
    '''
    The goal of #33 evaluated a second time, after the first evaluation
    narrowed its variable.  The generator of the variable stays in the graph;
    the second evaluation registers the variables of the generator and
    derives the bindings again.
    '''
    P = curry.import_('Prelude')
    xs = curry.free()
    goal = curry.expr(
        P.cond
      , curry.expr(P.constrEq, curry.expr(getattr(P, '++'), xs, [3]), [1, 2, 3])
      , xs
      )
    self.assertEqual(values(goal), [[1, 2]])
    self.assertEqual(values(goal), [[1, 2]])

  def test_cyclic_goal(self):
    '''
    A cyclic goal that holds a marker evaluates: let a = x : a in (x =:= 1)
    &> take 2 a gives [1, 1].  The variable of the marker was created before,
    so the walk of set_goal must cross the cycle to register it.
    '''
    P = curry.import_('Prelude')
    x = curry.free()
    create_variable(x)
    goal = curry.expr(
        P.cond
      , curry.expr(P.constrEq, x, 1)
      , curry.expr(P.take, 2, anchor(cons(x, ref())))
      )
    self.assertEqual(values(goal), [[1, 1]])

  def test_compile_expr_let_free(self):
    '''
    ``let xs free`` inside a text expression.  The single rewrite step of
    compile(mode='expr') creates the variable in a state that is discarded;
    the evaluation of the result registers it.
    '''
    goal = curry.compile(
        'let xs free in (xs ++ [3] =:= [1,2,3]) &> xs'
      , mode='expr', exprtype='[Int]'
      )
    self.assertEqual(values(goal), [[1, 2]])

  def test_registration(self):
    '''
    set_goal registers the free variables the goal already holds, in the
    table of the new state, on both backends.
    '''
    P = curry.import_('Prelude')
    interp = curry.getInterpreter()
    x = curry.free()
    node = create_variable(x)
    vid = inspect.get_freevar_id(node)
    rts = interp.backend.create_evaluation_rts(interp, curry.expr(P.id, x))
    self.assertIn(vid, rts.vtable)
    self.assertIs(rts.vtable[vid], node)

  def test_counter(self):
    '''
    The walk of set_goal runs only after the interpreter made a free variable
    outside an evaluation: a marker of curry.free, a raw Free node of
    curry.raw_expr, a variable of a single step, or a variable copied into
    a value.  The counter is InterpreterState.external_freevars on both
    backends.
    '''
    P = curry.import_('Prelude')
    interp = curry.getInterpreter()
    istate = interpreter_state()
    self.assertEqual(istate.external_freevars, 0)
    curry.expr(P.id, 1)
    self.assertEqual(istate.external_freevars, 0)
    x = curry.free()
    curry.expr((x, x))
    self.assertEqual(istate.external_freevars, 2)
    raw = curry.raw_expr(free(1000))
    self.assertEqual(istate.external_freevars, 3)
    # With the counter at zero, the goal is not walked.
    istate.external_freevars = 0
    rts = interp.backend.create_evaluation_rts(interp, curry.expr(P.id, raw))
    self.assertEqual(dict(rts.vtable), {})
    del rts
    istate.external_freevars = 1
    rts = interp.backend.create_evaluation_rts(interp, curry.expr(P.id, raw))
    self.assertEqual(list(rts.vtable), [1000])

  def test_single_step_counts_variables(self):
    '''
    The variables of a single rewrite step outlive its state: the state
    counts them, so that the next goal is walked.
    '''
    P = curry.import_('Prelude')
    interp = curry.getInterpreter()
    istate = interpreter_state()
    e = curry.expr(curry.free())
    istate.external_freevars = 0
    evaluator.single_step(interp, e)
    self.assertIsaFreevar(inspect.fwd_chain_target(e))
    self.assertGreaterEqual(istate.external_freevars, 1)
    self.assertEqual(values(P.constrEq, e, 1), [True])

  def test_iterator_item(self):
    '''
    A marker inside a lazy iterator reaches the graph when the generator
    step runs, after set_goal walked the goal.  The step registers the free
    variables of the item: the goal of #33 with xs behind iter([xs]) gives
    [1, 2] after an earlier evaluation created the variable.
    '''
    P = curry.import_('Prelude')
    xs = curry.free()
    create_variable(xs)
    goal = curry.expr(
        P.cond
      , curry.expr(
            P.constrEq
          , curry.expr(getattr(P, '++'), curry.expr(P.head, iter([xs])), [3])
          , [1, 2, 3]
          )
      , curry.expr(P.head, iter([xs]))
      )
    self.assertEqual(values(goal), [[1, 2]])

  def test_value_with_free_variable(self):
    '''
    A value of one evaluation that holds a free variable, placed in a later
    goal.  No marker and no single step made the variable, so the copy of
    the value counts it; the later goal is walked and gives [1, 2].
    '''
    P = curry.import_('Prelude')
    istate = interpreter_state()
    M = curry.compile('g :: [Int]\ng = xs where xs free\n', mode='module')
    self.assertEqual(istate.external_freevars, 0)
    v, = curry.eval(M.g)
    self.assertIsaFreevar(v)
    self.assertGreaterEqual(istate.external_freevars, 1)
    goal = curry.expr(
        P.cond
      , curry.expr(P.constrEq, curry.expr(getattr(P, '++'), v, [3]), [1, 2, 3])
      , v
      )
    self.assertEqual(values(goal), [[1, 2]])

  def test_reset(self):
    '''
    curry.reset installs a new interpreter state with a new id factory.  A
    marker built under the old state gets a new node under the new one, so
    it does not share an id with a marker made after the reset.
    '''
    P = curry.import_('Prelude')
    x = curry.free()
    before = create_variable(x)
    curry.reset()
    y = curry.free()
    self.assertIsNot(curry.expr(x), before)
    self.assertEqual(values(P.constrEq, (x, y), (1, 2)), [True])

  def test_raw_expr(self):
    '''raw_expr keeps the raw Free node with the id of the marker.'''
    self.assertEqual(repr(curry.raw_expr(free(5))), '<_Free 5 <()>>')
    e = curry.raw_expr((free(5), free(5)))
    first, second = e[0], e[1]
    self.assertIsNot(first, second)


class TestChoiceMarkers(cytest.TestCase):
  '''``curry.choice`` through ``curry.expr`` and ``curry.eval``.'''

  def test_fresh_ids(self):
    '''
    Each choice gets its own id from the runtime: two choices in one goal
    give four values.  (Two raw choices with the id 0 would give two.)
    '''
    goal = curry.expr((curry.choice(1, 2), curry.choice(3, 4)))
    self.assertEqual(sorted(values(goal)), [(1, 3), (1, 4), (2, 3), (2, 4)])

  def test_choice_node(self):
    '''
    The marker becomes a call of Prelude.?; one step makes a choice whose id
    is fresh, so two markers get two ids.
    '''
    P = curry.import_('Prelude')
    interp = curry.getInterpreter()
    e1, e2 = curry.expr(curry.choice(1, 2)), curry.expr(curry.choice(3, 4))
    self.assertEqual(e1.info.name, getattr(P, '?').info.name)
    self.assertEqual(str(e1), '(?) 1 2')
    evaluator.single_step(interp, e1)
    evaluator.single_step(interp, e2)
    c1, c2 = inspect.fwd_chain_target(e1), inspect.fwd_chain_target(e2)
    self.assertIsaChoice(c1)
    self.assertIsaChoice(c2)
    self.assertNotEqual(inspect.get_choice_id(c1), inspect.get_choice_id(c2))

  def test_raw_expr(self):
    '''raw_expr keeps the raw Choice node with the id of the marker.'''
    self.assertEqual(
        repr(curry.raw_expr(choice(1, True, False)))
      , '<_Choice 1 <True> <False>>'
      )

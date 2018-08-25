import cytest # from ./lib; must be first
from curry.interpreter import runtime
from curry.runtime import LEFT, RIGHT
import curry

class TestPyPullTab(cytest.TestCase):
  def testPullChoice(self):
    '''Tests the pull-tab step for choices.'''
    module = curry.compile('f (_,_,9) True a = a', modulename='M')
    goal = curry.compile('M.f (1,2,8?9) True (1,2,3)', mode='expr')
    interp = curry.getInterpreter()
    id8 = id(goal[0][2][0])
    id9 = id(goal[0][2][1])
    id123 = id(goal[2])
    # Head-normalizing brings a choice to the root.
    self.assertRaises(runtime.E_SYMBOL, lambda: interp.hnf(goal))
    self.assertEqual(goal.info.tag, runtime.T_CHOICE)
    # Ensure nodes are referenced, not copied.
    # LHS -> failure
    self.assertEqual(id(goal[1][2]), id8)
    self.assertEqual(id(goal[1][1]), id123)
    self.assertRaises(runtime.E_SYMBOL, lambda: interp.hnf(goal[1]))
    self.assertEqual(goal[1].info.tag, runtime.T_FAIL)
    # RHS -> True
    self.assertEqual(id(goal[2][2]), id9)
    self.assertEqual(id(goal[2][1]), id123)
    self.assertMayRaise(None, lambda: interp.hnf(goal[2]))
    self.assertEqual(curry.topython(id(goal[2][()])), id123)


  def testPullEqChoices(self):
    '''Tests the pull-tab step for the EqChoices constraint.'''
    I = curry.getInterpreter()
    u = curry.unboxed
    constraint = curry.expr(I.prelude._EqChoices, True, (u(101), u(102)))
    e = curry.expr([(0, constraint, 1)])
    runtime.pull_tab(I, e, [0,1])
    self.assertIs(e.info, I.prelude._EqChoices.info)
    self.assertEqual(curry.topython(e[0]), [(0, True, 1)])
    self.assertEqual(curry.topython(e[1]), (101, 102))

  def testPullChoiceConstr(self):
    '''Tests the pull-tab step for the ChoiceConstr constraint.'''
    I = curry.getInterpreter()
    u = curry.unboxed
    constraint = curry.expr(I.prelude._ChoiceConstr, True, (u(109), u(LEFT)))
    e = curry.expr([(0, constraint, 1)])
    runtime.pull_tab(I, e, [0,1])
    self.assertIs(e.info, I.prelude._ChoiceConstr.info)
    self.assertEqual(curry.topython(e[0]), [(0, True, 1)])
    self.assertEqual(curry.topython(e[1]), (109, LEFT))
    #
    constraint = curry.expr(I.prelude._ChoiceConstr, True, (u(109), u(RIGHT)))
    e = curry.expr([(0, constraint, 1)])
    runtime.pull_tab(I, e, [0,1])
    self.assertIs(e.info, I.prelude._ChoiceConstr.info)
    self.assertEqual(curry.topython(e[0]), [(0, True, 1)])
    self.assertEqual(curry.topython(e[1]), (109, RIGHT))

  def testPullEqVarsConstr(self):
    '''Tests the pull-tab step for the EqVars constraint.'''
    I = curry.getInterpreter()
    u = curry.unboxed
    unknown = I.symbol('Prelude.unknown')
    q = I.symbol('Prelude.?')
    x,y = list(I.eval(q, unknown, unknown))
    constraint = curry.expr(I.prelude._EqVars, 314, (x, y))
    e = curry.expr([(0, constraint, 1)])
    runtime.pull_tab(I, e, [0,1])
    self.assertIs(e.info, I.prelude._EqVars.info)
    self.assertEqual(curry.topython(e[0]), [(0, 314, 1)])
    self.assertEqual(curry.topython(e[1]), (x, y))
    

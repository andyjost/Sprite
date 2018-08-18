import cytest # from ./lib; must be first
from curry.interpreter import runtime
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


  def testPullConstraint(self):
    '''Tests the pull-tab step for constraints.'''
    I = curry.getInterpreter()
    u = curry.unboxed
    constraint = curry.expr(I.prelude._EqChoices, True, (u(101), u(102)))
    e = curry.expr([(0, constraint, 1)])
    runtime.pull_tab(I, e, [0,1])
    self.assertIs(e.info, I.prelude._EqChoices.info)
    self.assertEqual(curry.topython(e[0]), [(0, True, 1)])
    self.assertEqual(curry.topython(e[1]), (101, 102))

import cytest # from ./lib; must be first
from curry.common import *
from curry.backends.py.eval.rts import RuntimeState
from curry.backends.generic.eval.control import E_UNWIND
from curry.backends.py.eval.fairscheme import hnf
import curry, unittest

class TestPyPullTab(cytest.TestCase):
  def testPullChoice(self):
    '''Tests the pull-tab step for choices.'''
    module = curry.compile('f (_,_,9) True a = a', modulename='M')
    interp = curry.getInterpreter()
    P = interp.prelude
    goal = curry.raw_expr( # id (M.f (1,2,8?9) True (1,2,3))
        P.id
      , [module.f
          , (1, 2, [getattr(P, '?'), 8, 9])
          , P.True_
          , (1, 2, 3)
          ]
      )
    id8 = id(goal[0,0,2,0])
    id9 = id(goal[0,0,2,1])
    id123 = id(goal[0,2])
    # Head-normalizing brings a choice to the root.
    goal0 = goal[0]
    rts = RuntimeState(interp, goal0)
    self.assertRaises(E_UNWIND, lambda: hnf(rts, rts.variable(goal0, [0,2])))
    # goal = id (f...8 ? f...9)
    self.assertEqual(goal0.info.tag, T_CHOICE)
    # Ensure nodes are referenced, not copied.
    # LHS -> failure
    lhs = goal[0,1]
    self.assertEqual(id(lhs[0,2]), id8)
    self.assertEqual(id(lhs[2]), id123)
    lhs = curry.raw_expr(interp.prelude.id, lhs) # id (f...8)
    self.assertRaises(E_UNWIND, lambda: hnf(rts, rts.variable(lhs, 0)))
    self.assertEqual(lhs.info.tag, T_FAIL)
    # RHS -> True
    rhs = goal[0,2]
    self.assertEqual(id(rhs[0,2]), id9)
    self.assertEqual(id(rhs[2]), id123)
    rhs = curry.raw_expr(interp.prelude.id, rhs) # id (f...9)
    self.assertMayRaise(None, lambda: hnf(rts, rts.variable(rhs, 0)))
    self.assertEqual(id(rhs[0]), id123)

  @unittest.skip('constraints not implemented')
  def testPullEqChoices(self):
    '''Tests the pull-tab step for the EqChoices constraint.'''
    interp = curry.getInterpreter()
    rts = RuntimeState(interp)
    u = curry.unboxed
    constraint = curry.raw_expr(
        interp.prelude._EqChoices, True, (u(101), u(102))
      )
    e = curry.raw_expr(interp.prelude.id, [(0, constraint, 1)])
    pyruntime.pull_choice(rts, e, [0,0,1])
    self.assertIs(e.info, interp.prelude._EqChoices.info)
    self.assertEqual(curry.topython(e[0][0]), [(0, True, 1)])
    self.assertEqual(curry.topython(e[1]), (101, 102))

  @unittest.skip('constraints not implemented')
  def testPullChoiceConstr(self):
    '''Tests the pull-tab step for the ChoiceConstr constraint.'''
    interp = curry.getInterpreter()
    rts = RuntimeState(interp)
    u = curry.unboxed
    constraint = curry.raw_expr(
        interp.prelude._ChoiceConstr, True, (u(109), u(LEFT))
      )
    e = curry.raw_expr(interp.prelude.id, [(0, constraint, 1)])
    pyruntime.pull_choice(rts, e, [0,0,1])
    self.assertIs(e.info, interp.prelude._ChoiceConstr.info)
    self.assertEqual(curry.topython(e[0][0]), [(0, True, 1)])
    self.assertEqual(curry.topython(e[1]), (109, LEFT))

    constraint = curry.raw_expr(
        interp.prelude._ChoiceConstr, True, (u(109), u(RIGHT))
      )
    e = curry.raw_expr(interp.prelude.id, [(0, constraint, 1)])
    pyruntime.pull_choice(rts, e, [0,0,1])
    self.assertIs(e.info, interp.prelude._ChoiceConstr.info)
    self.assertEqual(curry.topython(e[0][0]), [(0, True, 1)])
    self.assertEqual(curry.topython(e[1]), (109, RIGHT))

  @unittest.skip('constraints not implemented')
  def testPullEqVarsConstr(self):
    '''Tests the pull-tab step for the EqVars constraint.'''
    interp = curry.getInterpreter()
    rts = RuntimeState(interp)
    u = curry.unboxed
    unknown = interp.symbol('Prelude.unknown')
    x = next(interp.eval(unknown))
    y = next(interp.eval(unknown))
    constraint = curry.raw_expr(interp.prelude._EqVars, 314, (x, y))
    e = curry.raw_expr(interp.prelude.id, [(0, constraint, 1)])
    pyruntime.pull_choice(rts, e, [0,0,1])
    self.assertIs(e.info, interp.prelude._EqVars.info)
    self.assertEqual(curry.topython(e[0][0]), [(0, 314, 1)])
    self.assertEqual(curry.topython(e[1]), (x, y))


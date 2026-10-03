'''Tests for the queue control and the trace helpers of the Python backend.'''
import cytest # from ./lib; must be first
from curry.backends.generic.eval import trace
from curry.backends.generic.eval.control import (
    E_RESIDUAL, E_RESTART, E_STEPLIMIT, E_UNWIND
  )
from curry.backends.py.eval import rts_control
from curry.backends.py.eval.configuration import Configuration
from curry.backends.py.eval.rts import RuntimeState
from curry.exceptions import EvaluationSuspended, NondetMonadError
import contextlib, curry, io, unittest

@unittest.skipIf(
    curry.flags['backend'] != 'py', 'drives the Python-backend RuntimeState directly'
  )
class TestPyControl(cytest.TestCase):
  def setUp(self):
    self.interp = curry.getInterpreter()
    self.P = self.interp.prelude

  def make_rts(self, *goals):
    '''Makes a runtime state with one configuration per goal.'''
    rts = RuntimeState(self.interp, curry.raw_expr(goals[0]))
    for goal in goals[1:]:
      rts.append(Configuration(curry.raw_expr(goal)))
    return rts

  def test_catch_control_unwind(self):
    rts = self.make_rts(1)
    def raise_unwind(**flags):
      with rts.catch_control(**flags):
        raise E_UNWIND()
    raise_unwind(unwind=True)
    self.assertRaises(E_UNWIND, raise_unwind)
    self.assertRaises(NondetMonadError, raise_unwind, nondet=True, unwind=True)

  def test_catch_control_residual(self):
    rts = self.make_rts(1, 2)
    head = rts.C
    def raise_residual(**flags):
      with rts.catch_control(**flags):
        raise E_RESIDUAL([7, 8])
    # Ground terms are required by default, so the residual propagates.
    self.assertRaises(E_RESIDUAL, raise_residual)
    raise_residual(ground=False)
    self.assertRaises(
        NondetMonadError, raise_residual, nondet=True, residual=True
      )
    self.assertIs(rts.C, head)
    # residual=True records the IDs and rotates the queue.
    raise_residual(residual=True)
    self.assertEqual(head.residuals, set([7, 8]))
    self.assertIsNot(rts.C, head)
    self.assertIs(rts.Q[-1], head)

  def test_catch_control_restart(self):
    rts = self.make_rts(1)
    def raise_restart(**flags):
      with rts.catch_control(**flags):
        raise E_RESTART()
    self.assertRaises(E_RESTART, raise_restart)
    raise_restart(restart=True)

  def test_catch_control_steplimit(self):
    rts = self.make_rts(1, 2)
    head = rts.C
    def raise_steplimit(qid=None, **flags):
      with rts.catch_control(**flags):
        raise E_STEPLIMIT(qid)
    self.assertRaises(E_STEPLIMIT, raise_steplimit)
    # The limit of an enclosing queue propagates.
    self.assertRaises(
        E_STEPLIMIT, raise_steplimit, qid=rts.qid + 1, steplimit=True
      )
    self.assertIs(rts.C, head)
    # The limit of this queue rotates it.
    raise_steplimit(steplimit=True)
    self.assertIs(rts.Q[-1], head)
    raise_steplimit(qid=rts.qid, steplimit=True)
    self.assertIs(rts.C, head)

  def test_catch_control_recursion(self):
    rts = self.make_rts(1, 2)
    head = rts.C
    def raise_recursion(**flags):
      with rts.catch_control(**flags):
        raise RecursionError('deep')
    self.assertRaises(RecursionError, raise_recursion)
    # The first overflow of a configuration rotates the queue.
    raise_recursion(steplimit=True)
    self.assertIs(rts.Q[-1], head)
    self.assertEqual(head.overflow_at, 0)
    rts.rotate()
    self.assertIs(rts.C, head)
    # A second overflow without a step drops the configuration.  The error
    # waits until the queue is empty.
    raise_recursion(steplimit=True)
    self.assertEqual(len(rts.Q), 1)
    self.assertIsNot(rts.C, head)
    self.assertIsInstance(rts.deferred_error, RecursionError)
    self.assertRaises(RecursionError, rts.raise_deferred_error)
    self.assertIsNone(rts.deferred_error)

  def test_catch_control_other(self):
    rts = self.make_rts(1)
    flags = dict(unwind=True, residual=True, restart=True, steplimit=True)
    with rts.catch_control(**flags):
      pass
    def raise_value_error():
      with rts.catch_control(**flags):
        raise ValueError('other')
    self.assertRaises(ValueError, raise_value_error)
    self.assertIsInstance(rts.catch_control(), rts_control.ControlHandler)

  def test_is_io(self):
    rts = self.make_rts(1)
    P = self.P
    self.assertTrue(rts.is_io(curry.raw_expr([P.prim_putChar, 'a'])))
    self.assertTrue(rts.is_io(curry.raw_expr([P.putStr, 'a'])))
    self.assertFalse(rts.is_io(curry.raw_expr([P.head, [1]])))
    self.assertRaises(AssertionError, rts.is_io, curry.raw_expr(1))
    self.assertIn('bindIO', rts_control.IO_FUNCTION_NAMES)

  def test_ready(self):
    # A head without residuals is ready.  The queue is not rotated.
    rts = self.make_rts(1, 2)
    head = rts.C
    self.assertTrue(rts.ready())
    self.assertIs(rts.C, head)
    # A blocked head is skipped.
    x = rts.freshvar()
    head.residuals.add(rts.obj_id(x))
    self.assertTrue(rts.ready())
    self.assertIsNot(rts.C, head)
    self.assertIs(rts.Q[-1], head)
    # When every configuration is blocked, the evaluation is suspended.
    rts.C.residuals.add(rts.obj_id(x))
    self.assertRaises(EvaluationSuspended, rts.ready)
    # An empty queue is not ready.
    rts.Q.clear()
    self.assertFalse(rts.ready())

  def test_queue_properties(self):
    rts = self.make_rts(1, 2)
    self.assertIs(rts.Q, rts.qtable[rts.qid])
    self.assertIs(rts.C, rts.Q[0])
    self.assertIs(rts.E, rts.C.root)
    root = curry.raw_expr(3)
    rts.E = root
    self.assertIs(rts.C.root, root)
    config = Configuration(curry.raw_expr(4))
    rts.C = config
    self.assertIs(rts.Q[0], config)
    queue = rts.Q.copy()
    rts.Q = queue
    self.assertIs(rts.qtable[rts.qid], queue)

  def test_trace_off(self):
    '''With tracing off, the trace helpers do no work.'''
    rts = self.make_rts(1)
    self.assertFalse(rts.tracing)
    self.assertIs(rts.trace.position(rts.E, [0]), trace.NULL_CONTEXT)
    self.assertIs(rts.trace.fork(), trace.NULL_CONTEXT)
    with rts.trace.position(rts.E, [0]):
      pass
    self.assertEqual(dict(rts.trace.indents), {})
    # The step tracer calls through.
    calls = []
    tracer = trace.trace_steps(lambda rts, node: calls.append(node))
    tracer(rts, rts.E)
    self.assertEqual(calls, [rts.E])

  @cytest.with_flags(trace=True)
  def test_trace_on(self):
    '''With tracing on, the steps and the values are printed.'''
    interp = curry.getInterpreter()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
      values = list(curry.eval(interp.prelude.id, 1))
    self.assertEqual(len(values), 1)
    self.assertIn('S <<<', out.getvalue())
    self.assertIn('S >>>', out.getvalue())
    self.assertIn('Y :::', out.getvalue())

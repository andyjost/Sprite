import cytest # from ./lib; must be first
import curry
from curry.interpreter import runtime
from curry import inspect

def step(interp, *args):
  expr = curry.expr(*args)
  expr.info.step(expr)
  return expr[()]

class TestInspect(cytest.TestCase):
  @classmethod
  def setUpClass(cls):
    reload(curry) # reset the choice ID factory.
    cls.interp = curry.getInterpreter()
    prelude = cls.interp.prelude
    cls.not_a_node = int
    cls.true = curry.expr(True)
    cls.false = curry.expr(False)
    cls.io = curry.expr(prelude.IO, prelude.True)
    cls.tuple_ = curry.expr((1,2,3))
    cls.list_ = curry.expr([1,2,3])
    cls.freevar = step(cls.interp, prelude.prim_unknown)
    cls.failure = step(cls.interp, prelude.failed)
    cls.fwd = curry.expr(prelude._Fwd, prelude.True)
    cls.choice = step(cls.interp, getattr(prelude, '?'), 0, 1)
    cls.func = curry.expr(prelude.head, getattr(prelude, '[]'))
    cls.everything = set([
        cls.true, cls.false, cls.io, cls.tuple_, cls.list_, cls.freevar
      , cls.failure, cls.choice, cls.func, cls.not_a_node
      ])

  @classmethod
  def tearDownClass(cls):
    keys = [k for k in  cls.__dict__ if not k.startswith('_')]
    for k in keys:
      delattr(cls, k)

  def check(self, f, obj):
    # f(obj) passes.
    self.assertTrue(f(self.interp, obj))
    # f(obj') fails for all obj' != obj.
    self.assertFalse(
        any(f(self.interp, x) for x in self.everything.difference([obj]))
      )

  def testIsaTypeError(self):
    self.assertIsa(curry.expr(1), curry.symbol('Prelude.Int'))
    self.assertRaisesRegexp(
        TypeError
      , 'arg 2 must be an instance or sequence of curry.interpreter.NodeInfo objects.'
      , lambda: inspect.isa(curry.expr(1), self.not_a_node)
      )

  def testIsaBool(self):
    self.check(inspect.isa_true, self.true)
    self.check(inspect.isa_false, self.false)

  def testIsaIO(self):
    self.check(inspect.isa_io, self.io)

  def testIsaTuple(self):
    self.check(inspect.isa_tuple, self.tuple_)

  def testIsaList(self):
    self.check(inspect.isa_list, self.list_)

  def testIsaFreevar(self):
    self.check(inspect.isa_freevar, self.freevar)

  def testIsaFailure(self):
    self.check(inspect.isa_failure, self.failure)

  def testIsaChoice(self):
    self.check(inspect.isa_choice, self.choice)

  def testIsaFunc(self):
    self.check(inspect.isa_func, self.func)

  def testIsaFwd(self):
    self.assertTrue(inspect.isa_fwd(self.interp, self.fwd))
    self.assertFalse(any(inspect.isa_fwd(self.interp, obj) for obj in self.everything))

  def testIsaCtor(self):
    self.assertTrue(
        all(inspect.isa_ctor(self.interp, obj)
            for obj in [self.true, self.false, self.io, self.tuple_, self.list_, self.fwd]
          )
      )
    self.assertFalse(
        any(inspect.isa_ctor(self.interp, obj)
            for obj in [self.freevar, self.failure, self.choice, self.func, self.not_a_node]
          )
      )

  def testGetID(self):
    self.assertEqual(inspect.get_id(self.interp, self.freevar), 0)
    self.assertEqual(inspect.get_id(self.interp, self.choice), 1)
    self.assertTrue(
        all(inspect.get_id(self.interp, x) is None)
            for x in self.everything.difference([self.freevar, self.choice]
          )
      )


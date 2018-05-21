import cytest # from ./lib; must be first
import curry

class TestPrelude(cytest.TestCase):

  def testPrimitiveBuiltins(self):
    eval_ = lambda e: curry.eval(e, converter=None)
    sym = lambda s: curry.symbol('Prelude.' + s)
    self.assertEqual(eval_([sym('=='), 3, 4]).next(), curry.expr(False))

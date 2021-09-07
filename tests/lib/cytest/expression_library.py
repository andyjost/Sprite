import curry
from . import testcase
from curry.expressions import (
    unboxed
  , _setgrd, fail, _strictconstr, _nonstrictconstr, _valuebinding, var, fwd
  , choice
  )

def vid():
  return 2

def cid():
  return 3

def sid():
  return 7

prelude = curry.import_('Prelude')
expressions = {
    'not_a_node': int
  , 'int': curry.expr(5)
  , 'unboxed_int': 5
  , 'char': curry.expr('a')
  , 'unboxed_char': 'a'
  , 'string': curry.expr('why hello')
  , 'empty_string': curry.expr('')
  , 'float': curry.expr(1.0)
  , 'unboxed_float': 1.0
  , 'just_nil': curry.expr(prelude.Just, [])
  , 'io': curry.expr(prelude.IO, prelude.True)
  , 'true': curry.expr(True)
  , 'false': curry.expr(False)
  , 'tuple': curry.expr((1,2,3))
  , 'list': curry.expr([1,2,3])
  , 'empty_list': curry.expr([])
  , 'py_generator': curry.expr(iter([1,2]))
  , 'failure': curry.expr(fail)
  , 'fwd': curry.expr(fwd(prelude.True))
  , 'var': curry.expr(var(vid()))
  , 'choice': curry.expr(choice(cid(), 0, 1))
  , 'nonstrict_constraint': curry.expr(_nonstrictconstr(True, (var(vid()), False)))
  , 'setgrd': curry.expr(_setgrd(sid(), True))
  , 'strict_constraint': curry.expr(_strictconstr(True, (var(1), var(2))))
  , 'value_binding': curry.expr(_valuebinding(True, (var(1), unboxed(2))))
  , 'func': curry.expr(prelude.head, getattr(prelude, '[]'))
  }

everything = set(expressions.values())

class ExpressionLibTestCase(testcase.TestCase):
  '''
  A subclass of TestCase that injects many Curry expressions into the object.
  '''
  @classmethod
  def setUpClass(cls):
    for name, expr in expressions.items():
      setattr(cls, name, expr)
    cls.everything = everything
    cls.vid = vid()
    cls.cid = cid()
    cls.sid = sid()
    super(ExpressionLibTestCase, cls).setUpClass()

  @classmethod
  def tearDownClass(cls):
    keys = [k for k in  cls.__dict__ if not k.startswith('_')]
    for k in keys:
      delattr(cls, k)
    super(ExpressionLibTestCase, cls).tearDownClass()

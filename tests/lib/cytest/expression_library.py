import curry
from . import testcase
from curry.expressions import (
    unboxed
  , _setgrd, fail, _strictconstr, _nonstrictconstr, _valuebinding, free, fwd
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
  , 'int': curry.raw_expr(5)
  , 'unboxed_int': 5
  , 'char': curry.raw_expr('a')
  , 'unboxed_char': 'a'
  , 'string': curry.raw_expr('why hello')
  , 'empty_string': curry.raw_expr('')
  , 'float': curry.raw_expr(1.0)
  , 'unboxed_float': 1.0
  , 'just_nil': curry.raw_expr(prelude.Just, [])
  , 'io': curry.raw_expr(prelude.IO, prelude.True_)
  , 'true': curry.raw_expr(True)
  , 'false': curry.raw_expr(False)
  , 'tuple': curry.raw_expr((1,2,3))
  , 'list': curry.raw_expr([1,2,3])
  , 'empty_list': curry.raw_expr([])
  , 'py_generator': curry.raw_expr(iter([1,2]))
  , 'failure': curry.raw_expr(fail)
  , 'fwd': curry.raw_expr(fwd(prelude.True_))
  , 'free': curry.raw_expr(free(vid()))
  , 'choice': curry.raw_expr(choice(cid(), 0, 1))
  , 'nonstrict_constraint': curry.raw_expr(_nonstrictconstr(True, (free(vid()), False)))
  , 'setgrd': curry.raw_expr(_setgrd(sid(), True))
  , 'strict_constraint': curry.raw_expr(_strictconstr(True, (free(1), free(2))))
  , 'value_binding': curry.raw_expr(_valuebinding(True, (free(1), unboxed(2))))
  , 'func': curry.raw_expr(prelude.head, getattr(prelude, '[]'))
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

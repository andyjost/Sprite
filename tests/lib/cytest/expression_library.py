from . import raw
import curry
from . import testcase
from curry.expressions import (
    _setgrd, fail, _strictconstr, _nonstrictconstr, _valuebinding, free, fwd
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
  , 'int': raw.expr(5)
  , 'unboxed_int': 5
  , 'char': raw.expr('a')
  , 'unboxed_char': 'a'
  , 'string': raw.expr('why hello')
  , 'empty_string': raw.expr('')
  , 'float': raw.expr(1.0)
  , 'unboxed_float': 1.0
  , 'just_nil': raw.expr(prelude.Just, [])
  , 'io': raw.expr(prelude.IO, prelude.True_)
  , 'true': raw.expr(True)
  , 'false': raw.expr(False)
  , 'tuple': raw.expr((1,2,3))
  , 'list': raw.expr([1,2,3])
  , 'empty_list': raw.expr([])
  , 'py_generator': raw.expr(iter([1,2]))
  , 'failure': raw.expr(fail)
  , 'fwd': raw.expr(fwd(prelude.True_))
  , 'free': raw.expr(free(vid()))
  , 'choice': raw.expr(choice(cid(), 0, 1))
  , 'nonstrict_constraint': raw.expr(_nonstrictconstr(True, (free(vid()), False)))
  , 'setgrd': raw.expr(_setgrd(sid(), True))
  , 'strict_constraint': raw.expr(_strictconstr(True, (free(1), free(2))))
  , 'value_binding': raw.expr(_valuebinding(True, (free(1), 2)))
  , 'func': raw.expr(prelude.head, getattr(prelude, '[]'))
  }

everything = set(expressions.values())

class ExpressionLibTestCase(testcase.TestCase):
  '''
from . import raw
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

'''
A pure-Python Curry interpreter.
'''
from . import import_
from . import prelude
from . import runtime
import itertools
import logging
import os
import sys

logger = logging.getLogger(__name__)

class Interpreter(object):
  '''
  A Curry interpreter.

  Use ``import_`` to add modules to the system.  Then use ``eval`` to evaluate
  expressions.

  Supported flags:
  ----------------
      ``debug`` (*True*|False)
          Sacrifice speed to add more consistency checks and enable debugging
          with PDB.
      ``defaultconverter`` ('topython'|*None*)
          Indicates the conversion to apply to results of eval.
      ``trace`` (True|*False*)
          Shows the effect of each step in a computation.
  '''
  def __new__(cls, flags={}):
    self = object.__new__(cls)
    self.stdin = sys.stdin
    self.stdout = sys.stdout
    self.stderr = sys.stderr
    self.modules = {}
    self.flags = {'debug':True, 'defaultconverter':None, 'trace':False}
    envflags = os.environ.get('SPRITE_INTERPRETER_FLAGS')
    if envflags is not None:
      self.flags.update({
          k:_flagval(v) for e in envflags.split(',') for k,v in [e.split(':')]
        })
    self.flags.update(flags)
    self.path = filter(lambda x:x, os.environ.get('CURRYPATH', '').split(':'))
    setattr(self, '.cache', {})
    self._idfactory_ = itertools.count()
    return self

  def __init__(self, flags={}):
    self.prelude = self.import_(
        "Prelude", extern=prelude.Prelude, export=prelude.exports()
      , alias=prelude.aliases()
      )
    self.step = runtime.get_stepper(self)

  # Externally-implemented methods.
  from .compile import compile
  from .conversions import box, currytype, expr, topython, unbox
  from .eval import eval
  from .import_ import import_
  from .lookup import module, symbol, type
  from .runtime import nf, hnf

# Misc.
# =====
def _flagval(v):
  '''Try to interpret the string ``v`` as a flag value.'''
  try:
    return {'True':True, 'False':False}[v]
  except KeyError:
    pass
  try:
    return int(v)
  except ValueError:
    pass
  return v


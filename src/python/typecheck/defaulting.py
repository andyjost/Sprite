'''
Defaulting of the class constraints of a goal, with the table of the PAKCS
REPL.

A goal whose scheme has class constraints cannot run as it is: every
constraint is a dictionary parameter.  The REPL of PAKCS picks a type for
each constrained type variable with a fixed table (``defaultQualType`` in
``c2p.pl``), and this module applies the same table:

  * ``Num`` and ``Integral`` default to ``Int``.
  * ``Fractional`` and ``Floating`` default to ``Float``.
  * ``Monad`` and ``MonadFail`` default to ``IO``.
  * ``Data``, ``Eq``, ``Ord``, ``Read`` and ``Show`` are dropped on a
    variable defaulted to ``Int`` or ``Float``; ``Enum`` is dropped on a
    variable defaulted to ``Int``; ``Monad`` is dropped on ``IO``.
  * A variable that carries ``Data`` alone defaults to ``Bool``.
  * Anything else is an error with the sentence of the oracle,
    ``Cannot handle arbitrary overloaded top-level expressions``.

A type variable without a constraint stays polymorphic.  A functional type
is accepted.  The table never substitutes ``()``.
'''

from .. import exceptions
from ..toolchain.flat2icurry import flatcurry as fc
from .sigtable import PRELUDE, Predicate, Scheme, show_scheme, show_type
import logging

logger = logging.getLogger(__name__)

__all__ = [
    'Defaulting', 'DefaultingError', 'ORACLE_SENTENCE', 'default_scheme'
  , 'normalize', 'substitute'
  ]

# The sentence the PAKCS REPL prints for a type its table cannot handle.
ORACLE_SENTENCE = 'Cannot handle arbitrary overloaded top-level expressions'

# Pass 1 of the table: a class that fixes the type of its variable.
DEFAULT_CLASSES = {
    'Prelude.Num'        : 'Int'
  , 'Prelude.Integral'   : 'Int'
  , 'Prelude.Fractional' : 'Float'
  , 'Prelude.Floating'   : 'Float'
  , 'Prelude.Monad'      : 'IO'
  , 'Prelude.MonadFail'  : 'IO'
  }

# Pass 2 of the table: a class that is dropped on a variable fixed in pass 1.
_DROPPED_ON_NUMBERS = frozenset([
    'Prelude.Data', 'Prelude.Eq', 'Prelude.Ord', 'Prelude.Read', 'Prelude.Show'
  ])
_ENUM_TYPES = frozenset(['Char', 'Int', 'Bool', 'Ordering'])
DATA_CLASS = 'Prelude.Data'
DATA_DEFAULT = 'Bool'

class DefaultingError(exceptions.CurryTypeError):
  '''
  The table cannot default the constraints of a scheme.

  Attributes:
    scheme:
        The scheme.
    predicate:
        The constraint the table rejected.
  '''
  def __init__(self, message, scheme, predicate=None):
    exceptions.CurryTypeError.__init__(self, message)
    self.scheme = scheme
    self.predicate = predicate

class Defaulting:
  '''
  The result of the table on one scheme.

  Attributes:
    scheme:
        The scheme as it came in.
    substitution:
        A dict from the index of a type variable to the name of the Prelude
        type it was defaulted to: ``Int``, ``Float``, ``IO`` or ``Bool``.
    typeexpr:
        The type with the substitution applied.  ``Apply`` of a defaulted
        constructor is folded (see :func:`normalize`).
    instances:
        One pair per constraint of the scheme, in the order of the scheme:
        the constraint and the qualified name of the type constructor whose
        instance satisfies it, e.g., ``Prelude.Int``.
    data_defaults:
        The indices of the variables that carried ``Data`` alone and were
        defaulted to ``Bool``.
  '''
  __slots__ = ('scheme', 'substitution', 'typeexpr', 'instances', 'data_defaults')

  def __init__(self, scheme, substitution, typeexpr, instances, data_defaults):
    self.scheme = scheme
    self.substitution = substitution
    self.typeexpr = typeexpr
    self.instances = instances
    self.data_defaults = data_defaults

  @property
  def changed(self):
    '''Whether the table defaulted anything.'''
    return bool(self.substitution)

  def show_type(self, module=None):
    '''The defaulted type in Curry syntax, e.g., ``Maybe Int``.'''
    return show_type(self.typeexpr, module=module)

  def __repr__(self):
    return '<Defaulting %s :: %s>' % (self.scheme.fullname, self.show_type())

def _dropped(classname, default):
  '''Whether a constraint of pass 2 is dropped on a variable fixed in pass 1.'''
  if classname in _DROPPED_ON_NUMBERS:
    return default in ('Int', 'Float')
  if classname == 'Prelude.Enum':
    return default in _ENUM_TYPES
  if classname == 'Prelude.Monad':
    return default == 'IO'
  return False

def _error(scheme, pred, what, hint):
  what = 'goal %s' % scheme.fullname if what is None else what
  lines = [
      'cannot handle the overloaded %s of type %s' % (what, show_scheme(scheme))
    , '  ' + ORACLE_SENTENCE
    ]
  if hint:
    lines.append('  ' + hint)
  return DefaultingError('\n'.join(lines), scheme, pred)

def default_scheme(scheme, what=None, hint='add a type signature', type_arity=None):
  '''
  Applies the table of the PAKCS REPL to a scheme.

  Args:
    scheme:
        A :class:`Scheme <curry.typecheck.Scheme>`.
    what:
        How the error names the goal, e.g., ``"expression '1+2'"``.  The
        default names the symbol of the scheme.
    hint:
        The last line of the error.
    type_arity:
        A function from the qualified name of a type constructor to its
        declared arity, or None; :func:`normalize` uses it to fold ``Apply``.

  Returns:
    A :class:`Defaulting`.

  Raises:
    DefaultingError:
        A constraint the table cannot handle.
  '''
  substitution = {}
  rest = []
  # Pass 1: the classes that fix a type.  The order of the context does not
  # matter; a later constraint on the same variable wins, as in the oracle.
  for pred in scheme.context:
    tvar = _typevar(pred)
    default = DEFAULT_CLASSES.get(pred.classname)
    if tvar is None or default is None:
      rest.append(pred)
    else:
      substitution[tvar] = default
  # Pass 2: the remaining constraints, walked in the reverse order of the
  # context as the oracle does (removeConstraints in c2p.pl).  The order
  # matters in one case: a Data constraint binds its variable to Bool, and
  # an Enum constraint on the same variable is dropped only when the walk
  # meets Data first, so [Enum a, Data a] gives Bool and [Data a, Enum a] is
  # an error.  The front end sorts a context by class name, so a goal always
  # presents [Data a, Enum a].
  data_defaults = []
  for pred in reversed(rest):
    tvar = _typevar(pred)
    if tvar is None:
      raise _error(scheme, pred, what, hint)
    default = substitution.get(tvar)
    if default is not None:
      if not _dropped(pred.classname, default):
        raise _error(scheme, pred, what, hint)
    elif pred.classname == DATA_CLASS:
      logger.info('Defaulting "Data" context to "Bool"...')
      substitution[tvar] = DATA_DEFAULT
      data_defaults.append(tvar)
    else:
      raise _error(scheme, pred, what, hint)
  mapping = {
      tvar: fc.TCons((PRELUDE, name), []) for tvar, name in substitution.items()
    }
  typeexpr = normalize(substitute(scheme.typeexpr, mapping), type_arity)
  instances = [
      (pred, '%s.%s' % (PRELUDE, substitution[_typevar(pred)]))
          for pred in scheme.context
    ]
  return Defaulting(scheme, substitution, typeexpr, instances, data_defaults)

def _typevar(pred):
  '''The index of the type variable of a constraint, or None.'''
  te = pred.typeexpr
  return te.index if isinstance(te, fc.TVar) else None

def substitute(typeexpr, mapping):
  '''Replaces the type variables of ``mapping`` (index to type) in a type.'''
  if isinstance(typeexpr, fc.TVar):
    return mapping.get(typeexpr.index, typeexpr)
  if isinstance(typeexpr, fc.FuncType):
    return fc.FuncType(
        substitute(typeexpr.domain, mapping), substitute(typeexpr.range, mapping)
      )
  if isinstance(typeexpr, fc.TCons):
    return fc.TCons(typeexpr.name, [substitute(a, mapping) for a in typeexpr.args])
  if isinstance(typeexpr, fc.ForallType):
    inner = {k: v for k, v in mapping.items() if k not in dict(typeexpr.typevars)}
    return fc.ForallType(typeexpr.typevars, substitute(typeexpr.typeexpr, inner))
  raise TypeError('not a type expression: %r' % (typeexpr,))

APPLY = (PRELUDE, 'Apply')

def normalize(typeexpr, type_arity=None):
  '''
  Folds ``Apply (T a1 .. an-1) an`` into ``T a1 .. an`` where the head is a
  type constructor.  A substitution can put a constructor at the head of an
  ``Apply``: ``return 5`` has the type ``m a`` and the table binds ``m`` to
  ``IO``, so the type is ``IO Int``, not ``Apply IO Int``.  With
  ``type_arity``, a function from the qualified name of a constructor to its
  declared arity, an application that would exceed the arity stays an
  ``Apply``; without it every such application is folded.
  '''
  if isinstance(typeexpr, fc.FuncType):
    return fc.FuncType(
        normalize(typeexpr.domain, type_arity), normalize(typeexpr.range, type_arity)
      )
  if isinstance(typeexpr, fc.ForallType):
    return fc.ForallType(typeexpr.typevars, normalize(typeexpr.typeexpr, type_arity))
  if isinstance(typeexpr, fc.TCons):
    args = [normalize(a, type_arity) for a in typeexpr.args]
    if typeexpr.name == APPLY and len(args) == 2:
      head, arg = args
      if isinstance(head, fc.TCons) and head.name != APPLY:
        arity = None if type_arity is None else type_arity('%s.%s' % head.name)
        if arity is None or len(head.args) < arity:
          return fc.TCons(head.name, list(head.args) + [arg])
    return fc.TCons(typeexpr.name, args)
  return typeexpr

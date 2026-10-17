"""Internal goals, dictionary defaulting, and the parsing of free declarations.

The term layer owns named variables and solve reports their bindings.
"""

from .. import exceptions, inspect
from ..backends.generic.eval import evaluator
from ..expressions import free as free_marker
from ..objects import CurryNodeInfo
from ..toolchain.flat2icurry import flatcurry as fc, terms
from ..utility import readcurry as rc
from .defaulting import DefaultingError, default_scheme
from .sigtable import INST_PREFIX, PRELUDE, scheme_of_function
import re

__all__ = [
    'Goal', 'dictionaries', 'defaulted_goal', 'flat_type_text', 'is_dictionary'
  , 'make_goal', 'scheme_from_flat_text', 'split_where_free', 'symbol_goal'
  , 'type_arity'
  ]

class Goal:
  '''An expression handed to the runtime once.'''
  __slots__ = ('_expr', 'text')

  def __init__(self, expr, text=None):
    self._expr = expr
    self.text = text

  @property
  def expr(self):
    return self._expr

  def evaluate(self, interp):
    '''
    Start the evaluation and return a generator of runtime nodes.

    The goal hands its node to the runtime state and keeps no reference to
    it.  The root of the configuration moves with the rewrites, but a
    reference to the original node keeps every node of the search above the
    live configurations reachable (the choices pulled to the root with their
    failed alternatives), so a holder of the node roots the history of the
    evaluation and each collection marks it.  The goal holds no node once the
    generator starts, so retaining it does not root the search history.

    Raises:
      ValueError:
          The goal was evaluated already.
    '''
    expr, self._expr = self._expr, None
    if expr is None:
      raise ValueError('the goal was evaluated already')
    results = evaluator.evaluate(interp, expr)
    return _values(interp, results)

  def __str__(self):
    return '<evaluated>' if self._expr is None else str(self._expr)

  def __repr__(self):
    return '<curry goal %r>' % self.text

def _values(interp, results):
  try:
    yield from results
    # The C++ backend applies the objects compiled in the background during
    # the evaluation here (backends.cxx.tiered).
    interp.backend.after_evaluation(interp)
  finally:
    # Closing this generator closes the evaluation, so that its counts
    # reach the totals of the interpreter now.
    close = getattr(results, 'close', None)
    if close is not None:
      close()

# A trailing free declaration belongs to the text parser.
_IDENT = r"[a-z_][A-Za-z0-9_']*"
_WHERE_FREE = re.compile(
    r'^(?P<expr>.*?)\s+where\s+(?P<vars>%s(?:\s*,\s*%s)*)\s+free\s*$'
        % (_IDENT, _IDENT)
  , re.S
  )

def split_where_free(text):
  '''
  Splits a trailing ``where x, y free`` from the text of a goal, as the REPL
  of PAKCS does (``splitWhereFree`` in ``c2p.pl``).  Returns the expression
  and the list of variable names; the list is empty when the text has no
  such clause.
  '''
  m = _WHERE_FREE.match(text)
  if m is None:
    return text, []
  names = [name.strip() for name in m.group('vars').split(',')]
  return m.group('expr'), names

# Dictionaries
# ============
def type_arity(interp):
  '''
  A function from the qualified name of a type constructor to its declared
  arity, or None for an unknown type; for :func:`.defaulting.normalize`.
  '''
  def arity(typename):
    decl = interp.sigtable.type_decl(typename)
    return None if decl is None else len(decl.typevars)
  return arity

def dictionaries(interp, defaulting):
  '''
  The dictionary nodes of a defaulted scheme: for each constraint, in the
  order of the scheme, the partial application of ``_inst#Class#Type`` to no
  argument.

  Raises:
    CurryTypeError:
        No loaded module declares the instance.
  '''
  nodes = []
  for pred, typename in defaulting.instances:
    inst = interp.sigtable.instance(pred.classname, typename)
    if inst is None:
      raise exceptions.CurryTypeError(
          'no instance for %s %s, needed by %s :: %s after defaulting'
              % (
                  pred.classname.rpartition('.')[2], typename.rpartition('.')[2]
                , defaulting.scheme.fullname, defaulting.scheme
                )
        )
    nodes.append(interp.expr(interp.symbol(inst.fullname)))
  return nodes

def defaulted_goal(interp, symbol, scheme, args=(), what=None, hint=None):
  '''
  The expression of a goal whose scheme has dictionary parameters: the
  symbol applied to one base instance per constraint and then to ``args``.
  With value parameters left over, the expression is a function value.

  Raises:
    DefaultingError:
        The table cannot default the constraints.
  '''
  kwds = {} if hint is None else {'hint': hint}
  defaulting = default_scheme(
      scheme, what=what, type_arity=type_arity(interp), **kwds
    )
  dicts = dictionaries(interp, defaulting)
  return interp.expr(symbol, *dicts, *args)

def symbol_goal(interp, symbol):
  '''
  The goal expression of a symbol evaluated on its own, or None when the
  symbol needs no dictionary: a function with a scheme whose leading
  parameters are dictionaries gets them.  A symbol without a scheme is left
  to the plain builder.
  '''
  if not isinstance(symbol, CurryNodeInfo) or symbol.info.arity == 0:
    return None
  scheme = symbol.scheme
  if scheme is None or not scheme.ndicts:
    return None
  return defaulted_goal(interp, symbol, scheme)

def is_dictionary(arg):
  '''
  Whether an argument of ``expr`` is a class dictionary: the symbol of an
  instance function, ``_inst#Class#Type``, a node built from one, or a list
  that starts with one.
  '''
  if isinstance(arg, list):
    return bool(arg) and is_dictionary(arg[0])
  if isinstance(arg, CurryNodeInfo):
    return arg.name.startswith(INST_PREFIX)
  if getattr(arg, 'info', None) is not None:
    return str(arg).lstrip('(').startswith(INST_PREFIX)
  return False

def make_goal(interp, args, exprtype=None, anchors=None):
  '''
  The :class:`Goal` of the arguments of ``curry.eval``: a goal object as it
  is, a symbol with dictionary parameters applied to its
  dictionaries, and anything else through ``interp.expr`` with
  ``exprtype`` and the keyword ``anchors``.  The typed builder of
  ``interp.expr`` supplies the dictionaries of a symbol applied to
  arguments, and types a lone symbol under ``exprtype``.
  '''
  from ..objects.terms import Term, check_refs, named_vars
  from .errors import ConversionError
  if len(args) == 1 and isinstance(args[0], str):
    raise ConversionError('a str goal needs curry.parse(text) for code or curry.term(text) for a String')
  if not anchors:
    check_refs(args)
  named_vars(args)
  if args and isinstance(args[0], Term):
    head = args[0]
    if head.symbol is not None and not head._args:
      args = (head.symbol._info, *args[1:])
  anchors = dict(anchors or {})
  if len(args) == 1 and not anchors:
    arg = args[0]
    if isinstance(arg, Goal):
      return arg
    if isinstance(arg, list) and len(arg) == 1:
      arg = arg[0]
    if exprtype is None:
      expr = symbol_goal(interp, arg)
      if expr is not None:
        return Goal(expr)
  try:
    return Goal(interp.expr(*args, exprtype=exprtype, **anchors))
  except DefaultingError as error:
    if len(args) != 1 or not isinstance(args[0], Term):
      raise
    term = args[0]
    message = 'cannot handle the overloaded goal %s of type %s' % (term, term._signature)
    message += '\nCannot handle arbitrary overloaded top-level expressions'
    if term.symbol is not None and term.symbol.name.isidentifier() \
        and not any(isinstance(arg, Term) for arg in term._args):
      module = term.symbol.module.__name__
      prefix = 'P' if module == 'Prelude' else module
      call = '%s.%s(%s)' % (prefix, term.symbol.name,
          ', '.join(repr(getattr(arg, 'value', arg)) for arg in term._args))
    else:
      call = 'goal'
    typename = ('Int' if term.symbol is not None
        and term.symbol.fullname == 'Prelude.read' else 'T')
    message += "\nstate the type: curry.term(%s, type=%r)" % (call, typename)
    raise DefaultingError(message, error.scheme, error.predicate) from None

# The scheme in a saved module
# ============================
def flat_type_text(scheme):
  '''The FlatCurry type of a scheme as text, for the footer of a saved module.'''
  return terms.showterm(scheme.flat_typeexpr)

def scheme_from_flat_text(symbol, text):
  '''
  The scheme of a symbol from the text :func:`flat_type_text` wrote.  The
  arity comes from the symbol.
  '''
  typeexpr = fc.decode(rc.parse(text))
  icur = symbol.icurry
  func = fc.Func(
      (icur.modulename, icur.name), symbol.info.arity, fc.Public, typeexpr
    , fc.External(icur.name)
    )
  return scheme_of_function(func)

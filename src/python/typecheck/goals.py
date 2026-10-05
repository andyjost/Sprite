'''
Goals: the expressions that ``curry.eval``, ``curry.compile(mode='expr')``,
the REPL and ``sprite-exec`` evaluate.

A goal without a type signature is a function whose leading parameters are
class dictionaries (issue #39).  This module builds the expression that runs
such a goal: it defaults the constrained type variables with the table of the
PAKCS REPL (:mod:`.defaulting`) and applies the goal to one base instance per
constraint, in the order of the scheme, each a partial application of
``_inst#Class#Type`` with one missing argument, as compiled code passes a
dictionary.  Value parameters that remain give a function value.  No front
end runs and no module is written.

The text route lifts the variables of a trailing ``where x, y free`` to
parameters of the compiled expression, as the REPL does, and the values of
such a goal come back as :class:`Bindings`, printed the way PAKCS prints
them: ``{xs=[1,2]} True``.
'''

from .. import exceptions
from ..expressions import free as free_marker
from ..objects import CurryNodeInfo
from ..toolchain.flat2icurry import flatcurry as fc, terms
from ..utility import readcurry as rc
from .defaulting import DefaultingError, default_scheme
from .sigtable import INST_PREFIX, PRELUDE, scheme_of_function
import re

__all__ = [
    'Bindings', 'Goal', 'check_application', 'dictionaries', 'defaulted_goal'
  , 'flat_type_text', 'is_dictionary', 'make_goal', 'scheme_from_flat_text'
  , 'split_tuple_text', 'split_where_free', 'symbol_goal', 'type_arity'
  ]

class Goal:
  '''
  An expression to evaluate.

  Attributes:
    raw_expr:
        The node to evaluate.  For a goal with free variables, a tuple of the
        value and the variables.
    freevars:
        The names of the lifted ``where ... free`` variables, in order.
    scheme:
        The scheme of the compiled expression, or None.
    text:
        The text of the goal, or None.
  '''
  __slots__ = ('raw_expr', 'freevars', 'scheme', 'text')

  def __init__(self, raw_expr, freevars=(), scheme=None, text=None):
    self.raw_expr = raw_expr
    self.freevars = tuple(freevars)
    self.scheme = scheme
    self.text = text

  def values(self, interp, results, convert=None):
    '''
    The values of the goal from the results of its evaluation.  Each result
    is converted with ``convert``; a goal with free variables yields
    :class:`Bindings`.
    '''
    try:
      for result in results:
        if self.freevars:
          parts = [result[i] for i in range(len(self.freevars) + 1)]
          raw = result
          if convert is not None:
            parts = [convert(interp, part) for part in parts]
            raw = None
          yield Bindings(parts[0], zip(self.freevars, parts[1:]), raw)
        elif convert is not None:
          yield convert(interp, result)
        else:
          yield result
    finally:
      # Closing this generator closes the evaluation, so that its counts
      # reach the totals of the interpreter now.
      close = getattr(results, 'close', None)
      if close is not None:
        close()

  def __str__(self):
    return str(self.raw_expr)

  def __repr__(self):
    return '<curry goal %r with free variables %s>' % (
        self.text, ', '.join(self.freevars)
      )

class Bindings:
  '''
  One value of a goal with ``where ... free`` variables, with the bindings
  of those variables.  Prints as PAKCS prints it: ``{xs=[1,2]} True``.

  Attributes:
    value:
        The value of the goal.
    bindings:
        A dict from the name of a variable to its binding, in the order of
        the declaration.
    raw:
        The Curry tuple of the value and the bindings, as the evaluation
        produced it, or None when the parts were converted to Python.  The
        tuple is printed as one expression, so that an unbound variable
        gets one name in every part.
  '''
  __slots__ = ('value', 'bindings', 'raw')

  def __init__(self, value, bindings, raw=None):
    self.value = value
    self.bindings = dict(bindings)
    self.raw = raw

  def __eq__(self, rhs):
    return isinstance(rhs, Bindings) and self.value == rhs.value \
        and self.bindings == rhs.bindings

  def __ne__(self, rhs):
    return not (self == rhs)

  def __hash__(self):
    return hash((self.value, tuple(self.bindings.items())))

  def texts(self):
    '''The text of the value and of each binding, in that order.'''
    from .. import show_value
    n = len(self.bindings) + 1
    if self.raw is not None:
      parts = split_tuple_text(str(self.raw), n)
      if parts is not None:
        return parts
    return [show_value(self.value)] + [
        show_value(value) for value in self.bindings.values()
      ]

  def __str__(self):
    texts = self.texts()
    return '{%s} %s' % (
        ', '.join(
            '%s=%s' % (name, text) for name, text in zip(self.bindings, texts[1:])
          )
      , texts[0]
      )

  def __repr__(self):
    return '<curry value %s>' % self

def split_tuple_text(text, n):
  '''
  Splits the text of a Curry tuple of ``n`` elements, ``(e1, ..., en)``, at
  its top-level commas.  Brackets, strings and character literals are
  skipped.  Returns None when the text is not such a tuple.
  '''
  if n < 2 or not (text.startswith('(') and text.endswith(')')):
    return None
  body = text[1:-1]
  parts = []
  depth = start = i = 0
  while i < len(body):
    c = body[i]
    if c == '"':
      i = _skip_string(body, i)
    elif c == "'" and (i == 0 or not (body[i - 1].isalnum() or body[i - 1] in "_'")):
      i = _skip_char(body, i)
    else:
      if c in '([{':
        depth += 1
      elif c in ')]}':
        depth -= 1
      elif c == ',' and depth == 0:
        parts.append(body[start:i].strip())
        start = i + 1
      i += 1
  parts.append(body[start:].strip())
  return parts if len(parts) == n and all(parts) else None

def _skip_string(text, i):
  '''The index after the string literal that opens at ``i``.'''
  j = i + 1
  while j < len(text):
    if text[j] == '\\':
      j += 2
    elif text[j] == '"':
      return j + 1
    else:
      j += 1
  return j

def _skip_char(text, i):
  '''The index after the character literal that opens at ``i``.'''
  j = i + 1
  if j < len(text) and text[j] == '\\':
    j += 2
  while j < len(text) and text[j] != "'":
    j += 1
  return j + 1

# The text route
# ==============
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

def check_application(args):
  '''
  Checks the arguments of ``curry.eval`` that apply a symbol to arguments.
  A symbol with dictionary parameters applied to anything but its
  dictionaries would take the first argument as a dictionary and build a
  wrong expression without a word; this raises instead.  A caller that
  passes the dictionaries first is left alone.

  Raises:
    CurryTypeError:
        The head symbol has dictionary parameters and the first argument is
        not a dictionary.
  '''
  if len(args) == 1 and isinstance(args[0], list):
    args = args[0]
  if len(args) < 2 or not isinstance(args[0], CurryNodeInfo):
    return
  head = args[0]
  scheme = head.scheme
  if scheme is None or not scheme.ndicts or is_dictionary(args[1]):
    return
  n = scheme.ndicts
  raise exceptions.CurryTypeError(
      'cannot apply %s :: %s to arguments: the symbol takes %d class %s '
      'before its value parameters, and curry.eval supplies them only for a '
      'goal without arguments; compile the call from text with '
      "curry.compile(..., mode='expr'), with exprtype for its type, or pass "
      'the dictionaries first'
          % (scheme.fullname, scheme, n, 'dictionary' if n == 1 else 'dictionaries')
    )

def make_goal(interp, args):
  '''
  The :class:`Goal` of the arguments of ``curry.eval``: a goal object as it
  is, a symbol with dictionary parameters applied to its dictionaries, and
  anything else through ``interp.expr`` after :func:`check_application`.
  '''
  if len(args) == 1:
    arg = args[0]
    if isinstance(arg, Goal):
      return arg
    if isinstance(arg, list) and len(arg) == 1:
      arg = arg[0]
    expr = symbol_goal(interp, arg)
    if expr is not None:
      return Goal(expr)
  check_application(args)
  return Goal(interp.expr(*args))

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

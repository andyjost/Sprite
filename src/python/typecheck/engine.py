'''
The engine: types one Python-built expression over the schemes of the front
end (item Y6 of the typed boundary, epic #48).

The engine is Algorithm J without levels.  A caller describes an expression
as a tree of specs: an :class:`App` of a symbol to arguments, a :class:`Lit`
for a Python value, a :class:`Free` marker, a :class:`Known` value whose
type the caller supplies, a :class:`List`, a :class:`Tuple`, an :class:`Iter`
and a :class:`Typed` annotation.  :class:`Problem` instantiates the scheme
of every symbol with fresh variables, unifies eagerly as it walks the tree,
and keeps the class predicates on the variables.  :meth:`Problem.solve`
reduces the predicates through the instances, defaults the ambiguous
numeric variables as the front end does, records the undefaulted scheme
(what ``:type`` prints), applies the table of the PAKCS REPL
(:mod:`.defaulting`), and resolves every predicate to a dictionary term.

After ``solve`` the caller asks the type of every spec, the dictionaries an
application takes, the type a literal resolved to, and the ``Data``
dictionary of a free variable.  :func:`materialize` is the reference
materializer: it builds the node of a solved problem through ``raw_expr``,
with the dictionaries in scheme order, ``apply`` chains for over-application
and newtype constructors erased.  The typed builder of ``curry.expr`` is its
production counterpart.
'''

from .. import exceptions
from ..objects import CurryNodeInfo
from ..toolchain.flat2icurry import flatcurry as fc
from ..toolchain.flat2icurry.terms import Char, showterm
from ..utility import strings
from . import errors, exprtype as exprtype_mod, terms, unify
from .defaulting import DefaultingError, default_scheme
from .instances import DATA_CLASS, DictTerm, InstanceEnv, NoInstance, Pred
from .sigtable import (
    PRELUDE, Predicate, Scheme, _Names, _collect_typevars, _is_tuple_name
  , show_predicate, show_type, typevar_name
  )
from .terms import APPLY, Naming, Rigid, Var, prune, tcons, whnf, zonk
import collections.abc, numbers

__all__ = [
    'App', 'DEFAULT_HINT', 'Free', 'ITERATOR_HINT', 'Iter', 'Known'
  , 'LOCATION_DEPTH', 'List', 'Lit', 'Problem', 'Spec', 'Tuple', 'Typed'
  , 'build', 'describe', 'infer', 'materialize', 'spec_of'
  ]

DEFAULT_HINT = 'add a type annotation (exprtype)'

# The line added to the error of the table when the constraint sits on the
# element type of an iterator, which the items never fix.
ITERATOR_HINT = (
    "the element type of an iterator is fixed when the expression is built; "
    "state it with curry.typed(iterator, '[T]')"
  )
# The width of the expression text in the message of the defaulting table.
WHAT_WIDTH = 60

# The number of nested positions a location names before it elides the
# rest: 'element 2 of the list in element 1 of the list in ... in the
# expression'.
LOCATION_DEPTH = 8
BOOL, INT, FLOAT, CHAR = (fc.prelude(n) for n in ('Bool', 'Int', 'Float', 'Char'))
LIST = fc.prelude('[]')

# The specs
# =========
class Spec:
  '''
  One node of the description of an expression.

  Attributes:
    type:
        The term of the node, after the problem typed it.
    parent, index:
        The spec this one is an argument of, and its position there.
    payload:
        An object of the caller, kept as it is: the node of a known value,
        the free marker, the iterator.
  '''
  __slots__ = ('type', 'parent', 'index', 'payload')

  def __init__(self, payload=None):
    self.type = None
    self.parent = None
    self.index = None
    self.payload = payload

class App(Spec):
  '''
  A symbol applied to arguments.  ``symbol`` is a ``CurryNodeInfo``, the
  qualified name of a symbol, or a :class:`Scheme`; each argument is a spec
  or a Python value :func:`spec_of` accepts.  After ``solve``: ``scheme``,
  ``preds`` (the predicates of the context, in order), ``dicts`` (their
  dictionary terms), ``erased`` (a newtype constructor, built as its
  argument).
  '''
  __slots__ = (
      'symbol', 'args', 'scheme', 'preds', 'params', 'param_roots', 'erased'
    , 'dicts'
    )

  def __init__(self, symbol, *args):
    Spec.__init__(self)
    self.symbol = symbol
    self.args = [spec_of(arg) for arg in args]
    self.scheme = None
    self.preds = ()
    self.params = ()
    self.param_roots = ()
    self.erased = False
    self.dicts = None

class Lit(Spec):
  '''
  A Python value: a bool, an int, a float, a str, or None.  An int is typed
  by a variable with ``Num``, a float by one with ``Fractional``; the
  expected type decides between ``Char`` and ``[Char]`` for a one-character
  string.  ``None`` is an error that names the expected type.
  '''
  __slots__ = ('value', 'pred', 'default')

  def __init__(self, value):
    Spec.__init__(self, value)
    self.value = value
    self.pred = None
    self.default = None

class Free(Spec):
  '''
  A free variable.  ``payload`` is the marker; two specs with one marker
  share one variable.  After ``solve``, ``dict`` is the ``Data`` dictionary
  of its type, or the placeholder of ``Bool`` for a polymorphic type.
  '''
  __slots__ = ('dict',)

  def __init__(self, marker=None):
    Spec.__init__(self, marker)
    self.dict = None

class Known(Spec):
  '''
  A value with a type the caller supplies: a FlatCurry type whose ``TVar``
  leaves become fresh variables, or a type in Curry syntax.  ``payload`` is
  the value, kept as it is.
  '''
  __slots__ = ('typeexpr',)

  def __init__(self, typeexpr, payload=None):
    Spec.__init__(self, payload)
    self.typeexpr = typeexpr

class List(Spec):
  '''A Python list: every item unifies with one element type.'''
  __slots__ = ('items', 'elem')

  def __init__(self, items):
    Spec.__init__(self)
    self.items = [spec_of(item) for item in items]
    self.elem = None

class Tuple(Spec):
  '''A Python tuple.  ``()`` is the unit; Curry has no 1-tuple.'''
  __slots__ = ('items',)

  def __init__(self, items):
    Spec.__init__(self)
    self.items = [spec_of(item) for item in items]

class Iter(Spec):
  '''
  A Python iterator: a list whose element type is fixed by the context and
  by the table, never by an item.
  '''
  __slots__ = ('elem',)

  def __init__(self, iterator=None):
    Spec.__init__(self, iterator)
    self.elem = None

class Typed(Spec):
  '''A nested annotation: ``spec`` at the type ``text``.'''
  __slots__ = ('spec', 'text')

  def __init__(self, spec, text):
    Spec.__init__(self)
    self.spec = spec_of(spec)
    self.text = text

def spec_of(*args):
  '''
  The spec of the arguments of ``curry.expr``: a spec as it is; a symbol
  with its arguments; a Python value; a list headed by a symbol as an
  application and any other list as a Curry list; a tuple; a free marker;
  a choice marker as a call of ``Prelude.?``; an iterator.
  '''
  if len(args) != 1:
    if args and isinstance(args[0], CurryNodeInfo):
      return App(args[0], *args[1:])
    raise exceptions.CurryTypeError(
        'invalid arguments after %r' % (args[0],) if args else 'no expression'
      )
  arg = args[0]
  if isinstance(arg, Spec):
    return arg
  if isinstance(arg, CurryNodeInfo):
    return App(arg)
  if arg is None or isinstance(arg, (bool, numbers.Real, str, bytes)):
    return Lit(arg)
  if isinstance(arg, list):
    if arg and isinstance(arg[0], CurryNodeInfo):
      return App(arg[0], *arg[1:])
    return List(arg)
  if isinstance(arg, tuple):
    return Tuple(arg)
  from .. import expressions
  if isinstance(arg, expressions.free):
    return Free(arg)
  if isinstance(arg, expressions.choice):
    return App('Prelude.?', arg.lhs, arg.rhs)
  if isinstance(arg, collections.abc.Iterator):
    return Iter(arg)
  if hasattr(arg, 'rvalue'):
    return spec_of(arg.rvalue)
  raise exceptions.CurryTypeError(
      'cannot type a %s; a Curry node needs its type: Known(typeexpr, node)'
          % type(arg).__name__
    )

# The problem
# ===========
class Problem:
  '''
  The typing of one expression.

  Args:
    interp:
        The interpreter.
    spec:
        The expression, as a spec or as the arguments of ``curry.expr``.
    exprtype:
        The expected type of the root, in Curry syntax, or None.  Its type
        variables are rigid.
    what:
        How the errors of the defaulting table name the expression; the
        default describes the spec.
    hint:
        The last line of those errors.
    module:
        The module whose type names an unqualified name in ``exprtype``
        prefers, or None.

  The constructor types the expression (phase 1); :meth:`solve` reduces,
  defaults and resolves (phase 2).  Both raise the errors of
  :mod:`curry.typecheck.errors`.
  '''
  def __init__(
      self, interp, spec, exprtype=None, what=None, hint=DEFAULT_HINT
    , module=None
    ):
    self.interp = interp
    self.env = InstanceEnv(interp)
    self.arity = self.env.arity
    self.root = spec if isinstance(spec, Spec) else spec_of(spec)
    self.exprtype = exprtype
    self.hint = hint
    self.module = module
    self._what = what
    self.specs = []
    self.apps = []
    self.lits = []
    self.frees = []
    self.knowns = []
    self.iters = []
    self._markers = {}
    self._env_vars = []
    self._current = None
    self._newtypes = {}
    self._char_lits = []
    self._ambiguity_done = False
    self.scheme = None
    self.defaulting = []
    self.solved = False
    self._infer()

  # Phase 1
  # -------
  def _infer(self):
    expected = None
    if self.exprtype is not None:
      expected = self._parse(self.exprtype)
    stack = [(self.root, expected, None, None)]
    while stack:
      spec, expected, parent, index = stack.pop()
      spec.parent, spec.index = parent, index
      self._current = spec
      self.specs.append(spec)
      children = self._enter(spec, expected)
      for i in reversed(range(len(children))):
        child, exp = children[i]
        stack.append((child, exp, spec, i))
    self._bind_char_literals()
    self._current = None

  def _parse(self, text):
    if isinstance(text, str):
      return exprtype_mod.parse_term(self.interp, text, self.module)
    return terms.instantiate(text, {})

  def _enter(self, spec, expected):
    if isinstance(spec, App):
      return self._enter_app(spec, expected)
    if isinstance(spec, Lit):
      self._enter_lit(spec, expected)
    elif isinstance(spec, Free):
      self._enter_free(spec, expected)
    elif isinstance(spec, Known):
      typeexpr = spec.typeexpr
      if isinstance(typeexpr, str):
        typeexpr, _ = exprtype_mod.parse_type(self.interp, typeexpr, self.module)
      mapping = {}
      spec.type = terms.instantiate(typeexpr, mapping)
      self._env_vars.extend(mapping.values())
      self.knowns.append(spec)
      self._expect(spec, expected)
    elif isinstance(spec, List):
      spec.elem = Var()
      spec.type = tcons('[]', spec.elem)
      self._expect(spec, expected)
      return [(item, spec.elem) for item in spec.items]
    elif isinstance(spec, Tuple):
      n = len(spec.items)
      if n == 1:
        raise errors.ConversionError(
            'Curry has no 1-tuple (at %s)' % self.location(spec)
          , where=self.location(spec)
          )
      vars = [Var() for _ in spec.items]
      spec.type = tcons('()') if n == 0 else fc.TCons(
          fc.prelude('(%s)' % (',' * (n - 1))), vars
        )
      self._expect(spec, expected)
      return list(zip(spec.items, vars))
    elif isinstance(spec, Iter):
      spec.elem = Var()
      spec.type = tcons('[]', spec.elem)
      self._env_vars.append(spec.elem)
      self.iters.append(spec)
      self._expect(spec, expected)
    elif isinstance(spec, Typed):
      spec.type = self._parse(spec.text)
      self._expect(spec, expected)
      return [(spec.spec, spec.type)]
    else:
      raise TypeError('not a spec: %r' % (spec,))
    return ()

  def _scheme_of(self, app):
    symbol = app.symbol
    if isinstance(symbol, Scheme):
      return symbol
    if isinstance(symbol, str):
      symbol = app.symbol = self.interp.symbol(symbol)
    return self.interp.sigtable.lookup(symbol, required=True)

  def _enter_app(self, app, expected):
    scheme = app.scheme = self._scheme_of(app)
    mapping = {}
    kinds = dict(scheme.typevars)
    app.preds = [
        Pred(p.classname, terms.instantiate(p.typeexpr, mapping, kinds), app, None, i)
            for i, p in enumerate(scheme.context)
      ]
    t = terms.instantiate(scheme.typeexpr, mapping, kinds)
    for pred in app.preds:
      self._attach(pred)
    params = []
    for i in range(len(app.args)):
      t = whnf(t, self.arity)
      if isinstance(t, fc.FuncType):
        params.append(t.domain)
        t = t.range
      elif isinstance(t, Var):
        domain, range_ = Var(), Var()
        self._unify(t, fc.FuncType(domain, range_), app)
        params.append(domain)
        t = range_
      else:
        raise errors.ArityError(
            scheme, i, len(app.args), where=self.location(app)
          )
    app.params = params
    app.type = t
    app.erased = self._is_newtype(scheme)
    self.apps.append(app)
    self._expect(app, expected)
    app.param_roots = [terms.prune(p) for p in params]
    return list(zip(app.args, params))

  def _is_newtype(self, scheme):
    if not scheme.is_constructor:
      return False
    found = self._newtypes.get(scheme.fullname)
    if found is None:
      result = scheme.typeexpr
      while isinstance(result, fc.FuncType):
        result = result.range
      decl = None
      if isinstance(result, fc.TCons):
        decl = self.interp.sigtable.type_decl('%s.%s' % result.name)
      found = self._newtypes[scheme.fullname] = isinstance(decl, fc.TypeNew)
    return found

  def _enter_lit(self, lit, expected):
    value = lit.value
    if isinstance(value, bool):
      lit.type = tcons('Bool')
    elif isinstance(value, numbers.Integral):
      self._literal_var(lit, 'Prelude.Num', tcons('Int'))
    elif isinstance(value, numbers.Real):
      self._literal_var(lit, 'Prelude.Fractional', tcons('Float'))
    elif isinstance(value, (str, bytes)):
      text = lit.value = strings.ensure_str(value)
      exp = None if expected is None else whnf(expected, self.arity)
      if len(text) != 1 \
          or (isinstance(exp, fc.TCons) and exp.name != CHAR and exp.args):
        # A string; also a one-character one under a type with arguments,
        # which only a list can fill: [a], Maybe a, or the application of a
        # type variable (fmap ord 'a').
        lit.type = tcons('[]', tcons('Char'))
      elif exp is not None and not isinstance(exp, Var):
        # Char, a nullary type such as Int (nothing fits; the message names
        # the character), a function type, or a rigid variable.
        lit.type = tcons('Char')
      else:
        # Under an open type a one-character string is a weak mark for
        # Char: a sibling can still make the type [Char], as in ['c', 'ab'];
        # what stays open at the end of phase 1 becomes Char.  See
        # _bind_char_literals and _check_char.
        var = Var()
        var.holders.append(lit)
        lit.type = var
        self._char_lits.append(lit)
    elif value is None:
      raise self._none_error(lit, expected)
    else:
      raise errors.ConversionError(
          'cannot convert %r of type %s at %s'
              % (value, type(value).__name__, self.location(lit))
        , where=self.location(lit), value=value
        )
    self.lits.append(lit)
    self._expect(lit, expected)

  def _literal_var(self, lit, classname, default):
    var = Var()
    var.holders.append(lit)
    lit.pred = Pred(classname, var, lit)
    lit.default = default
    var.preds.append(lit.pred)
    lit.type = var

  def _none_error(self, lit, expected):
    where = self.location(lit)
    if expected is None:
      lines = ['cannot convert None at %s; expected a Curry value' % where]
      expected_type = None
    else:
      expected_type = self.type_of_term(expected)
      lines = ['cannot convert None at %s; expected %s' % (where, self.show(expected))]
      head = whnf(expected, self.arity)
      if isinstance(head, fc.TCons) and head.name == fc.prelude('Maybe'):
        lines.append('  Prelude.Nothing is the empty value of Maybe')
    return errors.ConversionError(
        lines, where=where, expected=expected_type, value=None
      )

  def _enter_free(self, spec, expected):
    marker = spec.payload
    var = None if marker is None else self._markers.get(id(marker))
    if var is None:
      var = Var()
      if marker is not None:
        self._markers[id(marker)] = var
      self._env_vars.append(var)
    var.holders.append(spec)
    spec.type = var
    self.frees.append(spec)
    self._expect(spec, expected)

  # Unification and predicates
  # --------------------------
  def _expect(self, spec, expected):
    if expected is not None:
      self._unify(spec.type, expected, spec)

  def _unify(self, actual, expected, spec):
    try:
      unify.unify(actual, expected, self.arity, self._on_bind)
    except unify.UnifyError as err:
      raise self._mismatch(spec, actual, expected, err) from None

  def _on_bind(self, var, term):
    '''After a variable is bound: checks the free markers, reduces the predicates.'''
    head = whnf(term, self.arity)
    if isinstance(head, fc.FuncType):
      for holder in var.holders:
        if isinstance(holder, Free):
          where = self.location(self._current)
          raise errors.FreeFunctionError(
              where, self.show(head), actual=self.type_of_term(head)
            )
    for holder in var.holders:
      if isinstance(holder, Lit) and holder.pred is None \
          and isinstance(holder.value, str):
        self._check_char(holder, head)
    preds, var.preds = var.preds, []
    # The predicate of a literal first: its failure names the literal that
    # fixed the type, which reads better than a missing instance.
    preds.sort(key=lambda p: not isinstance(p.root().spec, Lit))
    for pred in preds:
      self._reduce(pred)

  def _attach(self, pred):
    '''Puts a predicate on its variable, or reduces it when its head is a constructor.'''
    t = whnf(pred.term, self.arity)
    if isinstance(t, Var):
      t.preds.append(pred)
    elif isinstance(t, fc.TCons) and t.name == APPLY \
        and isinstance(whnf(t.args[0], self.arity), Var):
      whnf(t.args[0], self.arity).preds.append(pred)
    else:
      self._reduce(pred)

  def _reduce(self, pred):
    try:
      residual = self.env.reduce(pred)
    except NoInstance as err:
      raise self._no_instance(err) from None
    for p in residual:
      self._attach(p)

  def _check_char(self, lit, head):
    '''
    A one-character string whose open type was bound: ``Char`` as it is,
    ``[Char]`` when the type is a list, else a conversion error.
    '''
    if isinstance(head, fc.TCons):
      if head.name == CHAR:
        return
      if head.name == LIST:
        self._unify(head.args[0], tcons('Char'), lit)
        return
    raise self._char_mismatch(lit, head)

  def _bind_char_literals(self):
    '''
    The one-character strings whose type stayed open through phase 1 are
    characters: a one-character string under a bare type variable is a
    ``Char``.
    '''
    lits, self._char_lits = self._char_lits, []
    for lit in lits:
      if isinstance(prune(lit.type), Var):
        self._current = lit
        self._unify(lit.type, tcons('Char'), lit)

  def _char_mismatch(self, lit, term):
    '''The error of a one-character string whose open type another part fixed.'''
    where = self.location(lit)
    if isinstance(term, Rigid):
      return errors.ExprTypeMismatchError(
          term.source or self._exprtype_text(lit), 'Char', where=where
        , expected=self.type_of_term(term), actual=tcons('Char'), value=lit.value
        )
    ttext = self.show(term)
    lines = ['cannot convert %s to %s at %s' % (describe(lit), ttext, where)]
    fixed = self._fixed_by(lit)
    current = self._current
    if fixed:
      lines.append('  ' + fixed)
    elif current is not None and current is not lit:
      lines.append(
          '  %s has type %s (from %s)'
              % (self.short_location(current), ttext, describe(current))
        )
    return errors.ConversionError(
        lines, where=where, symbol=self._symbol_of(lit)
      , expected=self.type_of_term(term), actual=tcons('Char'), value=lit.value
      )

  # Errors
  # ------
  def _mismatch(self, spec, actual, expected, err):
    naming = Naming()
    etext = self.show(expected, naming)
    atext = self.show(actual, naming)
    where = self.location(spec)
    rigid = isinstance(err.lhs, Rigid) or isinstance(err.rhs, Rigid)
    annotated = isinstance(spec, Typed) or isinstance(spec.parent, Typed) \
        or (spec.parent is None and self.exprtype is not None)
    if rigid or (annotated and not isinstance(spec, Lit)):
      text = self._exprtype_text(spec)
      inferred = etext if isinstance(spec, Typed) else atext
      return errors.ExprTypeMismatchError(
          text, inferred, where=where, expected=self.type_of_term(expected)
        , actual=self.type_of_term(actual)
        )
    kwds = dict(
        where=where, symbol=self._symbol_of(spec)
      , expected=self.type_of_term(expected), actual=self.type_of_term(actual)
      )
    if isinstance(err, unify.OccursError):
      return errors.MismatchError(
          [ 'type mismatch in %s' % where
          , '  the type %s would contain itself in %s' % (etext, atext)
          ]
        , **kwds
        )
    fixed = self._fixed_by(spec)
    if isinstance(spec, Lit):
      lines = ['cannot convert %s to %s at %s' % (describe(spec), etext, where)]
      if fixed:
        lines.append('  ' + fixed)
      return errors.ConversionError(lines, value=spec.value, **kwds)
    lines = ['type mismatch in %s' % where]
    lines.append('  ' + fixed if fixed else '  expected %s' % etext)
    lines.append(
        '  %s has type %s (from %s)'
            % (self.short_location(spec), atext, describe(spec))
      )
    return errors.MismatchError(lines, **kwds)

  def _fixed_by(self, spec):
    '''The earlier argument that fixed the parameter type of ``spec``, or None.'''
    app = spec.parent
    if not isinstance(app, App) or spec.index is None:
      return None
    root = app.param_roots[spec.index]
    if not isinstance(root, Var):
      return None
    for j in range(spec.index):
      if app.param_roots[j] is root:
        return self._fixed_line(app, j, app.args[j], app.params[j])
    return None

  def _fixed_line(self, app, index, arg, term):
    letter = self._param_name(app.scheme, index)
    what = self.show(term)
    if letter is None:
      return 'argument %d fixed the type %s (from %s)' % (index + 1, what, describe(arg))
    return 'argument %d fixed %s := %s (from %s)' % (index + 1, letter, what, describe(arg))

  @staticmethod
  def _param_name(scheme, index):
    '''The name of the type variable of parameter ``index`` in the printed scheme.'''
    te = scheme.typeexpr
    for _ in range(index):
      if not isinstance(te, fc.FuncType):
        return None
      te = te.range
    if not isinstance(te, fc.FuncType) or not isinstance(te.domain, fc.TVar):
      return None
    names = _Names()
    _collect_typevars(scheme.typeexpr, names)
    for pred in scheme.context:
      _collect_typevars(pred.typeexpr, names)
    return names.names.get(te.domain.index)

  def _no_instance(self, err):
    pred, term = err.pred, err.term
    current = self._current
    where = self.location(current)
    root = pred.root()
    origin = root.spec
    predtext = show_predicate(
        Predicate(pred.classname, self.type_of_term(term)), names=None
      )
    predtext = self._short_class(predtext)
    if isinstance(term, Rigid):
      inferred = '%s => %s' % (predtext, self.show(self.root.type))
      return errors.ExprTypeMismatchError(
          term.source or self._exprtype_text(current), inferred
        , detail='the type variable %s of exprtype is rigid; the expression '
                 'needs %s' % (term.name, predtext)
        , where=where, actual=self.type_of_term(term)
        )
    if isinstance(origin, Lit):
      ttext = self.show(term)
      if origin is current:
        lines = ['cannot convert %s to %s at %s' % (describe(origin), ttext, where)]
        fixed = self._fixed_by(origin)
        if fixed:
          lines.append('  ' + fixed)
        return errors.ConversionError(
            lines, where=where, symbol=self._symbol_of(current)
          , value=origin.value, expected=self.type_of_term(term)
          )
      if isinstance(origin.parent, App):
        fixed = self._fixed_line(
            origin.parent, origin.index, origin, origin.default
          )
      else:
        fixed = '%s fixed the type %s (from %s)' % (
            self.short_location(origin), self.show(origin.default), describe(origin)
          )
      lines = [
          'type mismatch in %s' % where
        , '  ' + fixed
        , '  %s has type %s (from %s)'
              % (self.short_location(current), ttext, describe(current))
        ]
      return errors.MismatchError(
          lines, where=where, symbol=self._symbol_of(current)
        , expected=self.type_of_term(origin.default), actual=self.type_of_term(term)
        )
    if isinstance(origin, Free):
      where = 'the free variable at %s' % self.location(origin)
    return errors.NoInstanceError(
        pred.shortname, predtext.split(' ', 1)[1], where
      , symbol=self._symbol_of(current), actual=self.type_of_term(term)
      )

  @staticmethod
  def _short_class(predtext):
    '''``Prelude.Show (a -> a)`` as ``Show (a -> a)``.'''
    classname, _, rest = predtext.partition(' ')
    return '%s %s' % (classname.rpartition('.')[2], rest)

  def _exprtype_text(self, spec):
    while spec is not None:
      if isinstance(spec, Typed):
        return spec.text
      spec = spec.parent
    return self.exprtype if isinstance(self.exprtype, str) else '<type>'

  def _symbol_of(self, spec):
    parent = spec.parent
    while parent is not None and not isinstance(parent, App):
      parent = parent.parent
    return None if parent is None else parent.scheme.fullname

  # Locations
  # ---------
  def location(self, spec):
    '''
    The text of the position of a spec, e.g., ``argument 2 of Prelude.+ ::
    Num a => a -> a -> a`` or ``element 2 of the list in argument 1 of
    Prelude.length :: [a] -> Int``.  The chain ends at the nearest
    application or at the expression; a chain of more than
    :data:`LOCATION_DEPTH` positions is elided in the middle, so the text
    of a deeply nested value stays short.
    '''
    parts = []
    end = 'the expression'
    while spec is not None:
      parent = spec.parent
      if parent is None:
        break
      if isinstance(parent, App):
        end = 'argument %d of %s :: %s' % (
            spec.index + 1, parent.scheme.fullname, parent.scheme
          )
        break
      if isinstance(parent, List):
        parts.append('element %d of the list' % (spec.index + 1))
      elif isinstance(parent, Tuple):
        parts.append('component %d of the tuple' % (spec.index + 1))
      spec = parent
    if len(parts) > LOCATION_DEPTH:
      parts = parts[:LOCATION_DEPTH] + ['...']
    parts.append(end)
    return ' in '.join(parts)

  def short_location(self, spec):
    while spec is not None:
      parent = spec.parent
      if parent is None:
        break
      if isinstance(parent, App):
        return 'argument %d' % (spec.index + 1)
      if isinstance(parent, List):
        return 'element %d of the list' % (spec.index + 1)
      if isinstance(parent, Tuple):
        return 'component %d of the tuple' % (spec.index + 1)
      spec = parent
    return 'the expression'

  # Phase 2
  # -------
  @property
  def what(self):
    '''How the errors of the defaulting table name the expression.'''
    if self._what is not None:
      return self._what
    def make():
      text = describe(self.root)
      if len(text) > WHAT_WIDTH:
        text = text[:WHAT_WIDTH - 3] + '...'
      return "expression '%s'" % text
    return _LazyText(make)

  def solve(self):
    '''
    Phase 2: reduction, the defaulting of the front end, the table of the
    REPL, and the resolution of the dictionaries.  Returns the problem.
    '''
    if self.solved:
      return self
    self.scheme, _ = self._undefaulted()
    self._apply_table()
    for app in self.apps:
      self._current = app
      app.dicts = [self._resolve(pred) for pred in app.preds]
    for free in self.frees:
      self._current = free
      free.dict = self._resolve(Pred(DATA_CLASS, free.type, free))
    self._current = None
    self.solved = True
    return self

  def _live(self):
    '''The predicates not yet satisfied by an instance.'''
    live = []
    stack = []
    for app in reversed(self.apps):
      stack.extend(reversed(app.preds))
    for lit in reversed(self.lits):
      if lit.pred is not None:
        stack.append(lit.pred)
    seen = set()
    while stack:
      pred = stack.pop()
      if id(pred) in seen:
        continue
      seen.add(id(pred))
      if pred.instance is None:
        live.append(pred)
      else:
        stack.extend(reversed(pred.subpreds))
    return self.env.simplify(live)

  def _head_var(self, pred):
    t = whnf(pred.term, self.arity)
    if isinstance(t, Var):
      return t, True
    if isinstance(t, fc.TCons) and t.name == APPLY:
      head = whnf(t.args[0], self.arity)
      if isinstance(head, Var):
        return head, False
    return None, False

  def _undefaulted(self):
    '''
    The scheme the front end would infer: after its defaulting of the
    ambiguous numeric variables and before the table of the REPL.
    '''
    if not self._ambiguity_done:
      self._default_ambiguous()
      self._ambiguity_done = True
    return self._make_scheme()

  def _default_ambiguous(self):
    '''
    The rule of the front end: a constrained variable that occurs neither in
    the type of the expression nor in the environment is defaulted to the
    first of Int and Float with instances for all its classes, when one of
    them is numeric; otherwise it is an error.
    '''
    env = self.env
    while True:
      live = self._live()
      if not live:
        return
      fvs = set()
      for term in [self.root.type] + self._env_vars:
        fvs.update(terms.free_vars(term))
      groups = {}
      order = []
      for pred in live:
        var, direct = self._head_var(pred)
        if var is None:
          continue
        if var not in groups:
          groups[var] = []
          order.append(var)
        groups[var].append((pred, direct))
      bound = False
      for var in order:
        if var in fvs or var.find().binding is not None:
          continue
        classes = [p.classname for p, direct in groups[var] if direct]
        deferred = [p for p, direct in groups[var] if not direct]
        default = None
        if classes and not deferred and any(env.is_numeric(c) for c in classes):
          for name in ('Int', 'Float'):
            if all(env.has_instance(c, 'Prelude.' + name) for c in classes):
              default = name
              break
        if default is None:
          raise self._ambiguous(var, [p for p, _ in groups[var]])
        spec = groups[var][0][0].spec
        self._current = spec
        self._unify(var, tcons(default), spec)
        bound = True
      if not bound:
        return

  def _ambiguous(self, var, preds):
    scheme, naming = self._make_scheme()
    letter = typevar_name(naming.index(var))
    return errors.AmbiguousTypeError(
        describe(self.root), str(scheme)
      , detail='Ambiguous type variable %s in type %s' % (letter, scheme)
      , where='the expression', actual=scheme.typeexpr
      )

  def _make_scheme(self, preds=None, naming=None):
    '''The undefaulted scheme of the expression over the live predicates.'''
    live = self._live() if preds is None else preds
    naming = Naming() if naming is None else naming
    typeexpr = zonk(self.root.type, naming, self.arity)
    context = [
        Predicate(p.classname, zonk(p.term, naming, self.arity)) for p in live
      ]
    context.sort(key=_context_key)
    typevars = [(i, fc.KStar) for i in range(len(naming.leaves))]
    scheme = Scheme(
        '<expr>', 'expression', typevars, context, typeexpr, 0, len(context)
      )
    return scheme, naming

  def _apply_table(self):
    '''The table of the PAKCS REPL, until no predicate is left.'''
    while True:
      live = self._live()
      if not live:
        return
      naming = Naming()
      zonk(self.root.type, naming, self.arity)
      on_vars = [p for p in live if isinstance(whnf(p.term, self.arity), Var)]
      others = [p for p in live if p not in on_vars]
      kwds = dict(what=self.what, hint=self.hint, type_arity=self.arity)
      try:
        try:
          d = default_scheme(self._make_scheme(live, naming)[0], **kwds)
        except DefaultingError as err:
          pred = err.predicate
          if not others or not on_vars or pred is None \
              or isinstance(pred.typeexpr, fc.TVar):
            raise
          d = default_scheme(self._make_scheme(on_vars, naming)[0], **kwds)
      except DefaultingError as err:
        raise self._iterator_hint(err, naming) from None
      self.defaulting.append(d)
      if not d.substitution:
        return
      for index, name in d.substitution.items():
        leaf = naming.leaf(index)
        if isinstance(leaf, Var) and leaf.find().binding is None:
          spec = next(
              (p.spec for p in live if self._head_var(p)[0] is leaf.find())
            , self.root
            )
          self._current = spec
          self._unify(leaf, tcons(name), spec)

  def _iterator_hint(self, err, naming):
    '''
    The error of the table with one more line when the constraint it
    rejected sits on the element type of an iterator, which no item can
    fix: ``curry.typed(iterator, '[T]')`` states it.
    '''
    pred = err.predicate
    index = None if pred is None else _first_typevar(pred.typeexpr)
    if index is None or not self.iters:
      return err
    leaf = naming.leaves.get(index)
    if not isinstance(leaf, Var):
      return err
    leaf = leaf.find()
    if not any(it.elem.find() is leaf for it in self.iters):
      return err
    return DefaultingError(
        '%s\n  %s' % (err, ITERATOR_HINT), err.scheme, pred
      )

  def _resolve(self, pred):
    '''The dictionary term of a predicate; reduces it when needed.'''
    if pred.instance is None:
      var, _ = self._head_var(pred)
      if var is not None:
        if pred.classname == DATA_CLASS:
          return self.placeholder()
        raise errors.AmbiguousTypeError(
            describe(self.root), str(self.scheme)
          , detail='the constraint %s stays unresolved' % self._short_class(
                show_predicate(Predicate(pred.classname, self.type_of_term(pred.term)))
              )
          )
      self._reduce(pred)
    return DictTerm(pred.instance, [self._resolve(sub) for sub in pred.subpreds])

  def placeholder(self):
    '''The dictionary of a polymorphic free variable: ``Data Bool``, unread.'''
    return DictTerm(self.env.instance(DATA_CLASS, 'Prelude.Bool'))

  # Queries
  # -------
  def type_of_term(self, term, naming=None):
    return zonk(term, Naming() if naming is None else naming, self.arity)

  def type_of(self, spec, naming=None):
    '''The type of a spec as a FlatCurry type.'''
    return self.type_of_term(spec.type, naming)

  def show(self, term, naming=None):
    '''A term in Curry syntax.'''
    naming = Naming() if naming is None else naming
    return naming.show(zonk(term, naming, self.arity))

  def show_type_of(self, spec):
    return self.show(spec.type)

  @property
  def typeexpr(self):
    '''The type of the expression, defaulted after ``solve``.'''
    return self.type_of(self.root)

  @property
  def signature(self):
    '''The undefaulted scheme in Curry syntax, what ``:type`` prints.'''
    if self.scheme is None:
      self.scheme, _ = self._undefaulted()
    return str(self.scheme)

  @property
  def defaulted_signature(self):
    return show_type(self.typeexpr)

  def dictionaries(self, app):
    '''The dictionary terms of an application, in the order of its scheme.'''
    return app.dicts

  def literal_type(self, lit):
    return self.type_of(lit)

  def literal_dictionary(self, lit):
    '''The ``Num`` or ``Fractional`` dictionary of a literal at its type, or None.'''
    if lit.pred is None:
      return None
    self._current = lit
    return self._resolve(lit.pred)

  def free_dictionary(self, free):
    return free.dict

def _first_typevar(typeexpr):
  '''The index of the first type variable of a FlatCurry type, or None.'''
  stack = [typeexpr]
  while stack:
    t = stack.pop()
    if isinstance(t, fc.TVar):
      return t.index
    if isinstance(t, fc.FuncType):
      stack.append(t.range)
      stack.append(t.domain)
    elif isinstance(t, fc.TCons):
      stack.extend(reversed(t.args))
    elif isinstance(t, fc.ForallType):
      stack.append(t.typeexpr)
  return None

def _context_key(pred):
  '''
  The order of a context as the front end writes it: by the first type
  variable of the predicate, in the order of the variables of the type,
  then by the class: ``(Num a, Fractional b) => (a, b)`` and ``(Data a, Num
  a, Show a) => a``.
  '''
  modulename, _, classname = pred.classname.rpartition('.')
  index = _first_typevar(pred.typeexpr)
  return (
      index is None, index or 0, modulename, classname, show_type(pred.typeexpr)
    )

def infer(interp, *args, **kwds):
  '''Types the arguments of ``curry.expr`` and solves; returns the :class:`Problem`.'''
  return Problem(interp, spec_of(*args), **kwds).solve()

# The description of a spec
# =========================
def _is_operator(name):
  return bool(name) and not (name[0].isalnum() or name[0] == '_')

def _literal_text(lit):
  value = lit.value
  if isinstance(value, bool):
    return 'True' if value else 'False'
  if isinstance(value, str):
    t = None if lit.type is None else whnf(lit.type)
    if isinstance(t, fc.TCons) and t.name in (CHAR, LIST):
      as_char = t.name == CHAR
    else:
      as_char = len(value) == 1
    if as_char and len(value) == 1:
      return showterm(Char(value))
    return '""' if not value else showterm(value)
  if value is None:
    return 'None'
  return showterm(value)

# The depth at which the description of a spec stops with an ellipsis.
DESCRIBE_DEPTH = 64

def describe(spec, depth=DESCRIBE_DEPTH):
  '''
  The text of a spec in Curry syntax, for messages.  A subtree deeper than
  ``depth`` prints as ``...``.
  '''
  names = {}
  def d(s, prec, depth=depth):
    if depth <= 0:
      return '...'
    depth -= 1
    if isinstance(s, App):
      name, modulename = _app_name(s)
      shown = name if modulename == PRELUDE else '%s.%s' % (modulename, name)
      args = s.args
      if _is_tuple_name(name) and len(args) == len(name) - 1:
        return '(%s)' % ', '.join(d(a, 0, depth) for a in args)
      if _is_operator(name) and len(args) == 2:
        text = '%s %s %s' % (d(args[0], 1, depth), shown, d(args[1], 1, depth))
        return '(%s)' % text if prec > 0 else text
      head = '(%s)' % shown if _is_operator(name) else shown
      if not args:
        return head
      text = ' '.join([head] + [d(a, 2, depth) for a in args])
      return '(%s)' % text if prec > 1 else text
    if isinstance(s, Lit):
      return _literal_text(s)
    if isinstance(s, Free):
      key = id(s) if s.payload is None else id(s.payload)
      name = names.get(key)
      if name is None:
        name = names[key] = '_' + typevar_name(len(names))
      return name
    if isinstance(s, Known):
      return '<value>'
    if isinstance(s, List):
      return '[%s]' % ', '.join(d(i, 0, depth) for i in s.items)
    if isinstance(s, Tuple):
      return '(%s)' % ', '.join(d(i, 0, depth) for i in s.items)
    if isinstance(s, Iter):
      return '<iterator>'
    if isinstance(s, Typed):
      return '(%s :: %s)' % (d(s.spec, 0, depth), s.text)
    return repr(s)
  return d(spec, 0)

class _LazyText:
  '''A text computed when it is first formatted.'''
  __slots__ = ('_make', '_text')

  def __init__(self, make):
    self._make = make
    self._text = None

  def __str__(self):
    if self._text is None:
      self._text = self._make()
    return self._text

def _app_name(app):
  symbol = app.symbol
  if isinstance(symbol, CurryNodeInfo):
    return symbol.name, symbol.icurry.modulename
  if isinstance(symbol, Scheme):
    return symbol.name, symbol.modulename
  modulename, _, name = str(symbol).rpartition('.')
  return name, modulename

# The reference materializer
# ==========================
def materialize(problem):
  '''
  Builds the node of a solved problem through ``raw_expr``: the
  dictionaries first in scheme order, ``apply`` chains for the arguments
  past the arity, a partial application for fewer, a newtype constructor as
  its argument and a bare one as ``Prelude.id``, one ``unknown`` node per
  free marker with the ``Data`` dictionary of its type, literals at their
  resolved types.  The typed builder of ``curry.expr`` is the production
  counterpart; this one serves the tests of the engine.
  '''
  problem.solve()
  interp = problem.interp
  raw = interp.raw_expr
  sym = interp.symbol
  apply_ = sym('Prelude.apply')
  cons, nil = sym('Prelude.:'), sym('Prelude.[]')
  shared = {}

  def dict_node(d):
    return raw(sym(d.fullname), *[dict_node(a) for a in d.args])

  def list_node(nodes):
    node = raw(nil)
    for item in reversed(nodes):
      node = raw(cons, item, node)
    return node

  def literal_node(lit):
    t = whnf(lit.type, problem.arity)
    value = lit.value
    name = t.name if isinstance(t, fc.TCons) else None
    if name == BOOL:
      return raw(bool(value))
    if name == INT:
      return raw(int(value))
    if name == FLOAT:
      return raw(float(value))
    if name == CHAR:
      return raw(value)
    if name == LIST:
      return list_node([raw(c) for c in value])
    # A type with a Num or a Fractional instance of its own: the literal
    # goes through the conversion method of the class, as compiled code
    # does in a polymorphic context.
    if isinstance(value, numbers.Integral):
      dictionary = dict_node(problem.literal_dictionary(lit))
      return raw(apply_, raw(sym('Prelude.fromInt'), dictionary), raw(int(value)))
    if isinstance(value, numbers.Real):
      dictionary = dict_node(problem.literal_dictionary(lit))
      return raw(apply_, raw(sym('Prelude.fromFloat'), dictionary), raw(float(value)))
    raise exceptions.CurryTypeError(
        'cannot build the literal %r at type %s' % (value, problem.show(lit.type))
      )

  def finish(spec, args):
    '''The node of a spec whose children are the nodes ``args``.'''
    if isinstance(spec, App):
      if spec.erased:
        if not args:
          return raw(sym('Prelude.id'))
        node, rest = args[0], args[1:]
      else:
        symbol = spec.symbol if isinstance(spec.symbol, CurryNodeInfo) \
            else sym(spec.scheme.fullname)
        direct = [dict_node(d) for d in spec.dicts] + args
        n = spec.scheme.arity
        node = raw(symbol, *direct[:n])
        rest = direct[n:]
      for extra in rest:
        node = raw(apply_, node, extra)
      return node
    if isinstance(spec, Lit):
      return literal_node(spec)
    if isinstance(spec, Free):
      marker = spec.payload
      node = marker._shared(interp) if hasattr(marker, '_shared') else None
      if node is not None:
        return node
      key = spec.type.find() if isinstance(spec.type, Var) else spec
      node = shared.get(key)
      if node is None:
        node = shared[key] = raw(sym('Prelude.unknown'), dict_node(spec.dict))
        if hasattr(marker, '_share'):
          marker._share(interp, node)
      return node
    if isinstance(spec, Known):
      return spec.payload
    if isinstance(spec, List):
      return list_node(args)
    if isinstance(spec, Tuple):
      return raw(tuple(args))
    if isinstance(spec, Iter):
      return raw(spec.payload)
    if isinstance(spec, Typed):
      return args[0]
    raise TypeError('not a spec: %r' % (spec,))

  # A post-order walk with an explicit stack: the depth of the tree does
  # not bound the depth of the Python stack.
  nodes = {}
  stack = [(problem.root, False)]
  while stack:
    spec, ready = stack.pop()
    children = _children(spec)
    if ready:
      nodes[id(spec)] = finish(spec, [nodes[id(c)] for c in children])
      continue
    stack.append((spec, True))
    for child in reversed(children):
      stack.append((child, False))
  return nodes[id(problem.root)]

def _children(spec):
  if isinstance(spec, App):
    return spec.args
  if isinstance(spec, (List, Tuple)):
    return spec.items
  if isinstance(spec, Typed):
    return [spec.spec]
  return ()

def build(interp, *args, **kwds):
  '''Types the arguments of ``curry.expr`` and builds the node.'''
  return materialize(infer(interp, *args, **kwds))

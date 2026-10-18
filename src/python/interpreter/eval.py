'''The lazy searches returned by Interpreter.eval and Interpreter.solve.'''

from . import conversions
from .. import backends, expressions, inspect
from ..objects import CurryNodeInfo
from ..objects.results import Answer, Bindings, Results, Stream
from ..objects.terms import Char, Term, Var, check_live, named_vars, term, walk_forms
from ..toolchain.flat2icurry import flatcurry as fc
from ..typecheck import goals
from ..typecheck.builder import _follow
from ..typecheck.builder import Description

IO = fc.prelude('IO')


def _legacy_description(value, legacy):
  stack = [value]
  while stack:
    value = stack.pop()
    if isinstance(value, legacy):
      return True
    if isinstance(value, (list, tuple)):
      stack.extend(value)
  return False


def _arguments(interp, args, kwds):
  check_live(args)
  if len(args) == 1:
    value = args[0]
    if isinstance(value, str) and not isinstance(value, Char):
      from ..typecheck.errors import ConversionError
      raise ConversionError('a str goal needs curry.parse(text) for code or curry.term(text) for a String')
    legacy = (
        Description, expressions.free, expressions.ref, expressions.typed
      , expressions.cons, expressions.unboxed, expressions.fwd, expressions.choice
      , expressions.anchor
      )
    if not isinstance(value, (Term, backends.Node, CurryNodeInfo, goals.Goal, *legacy)) \
        and not kwds and not _legacy_description(value, (*legacy, backends.Node)):
      # Raw symbol descriptions remain at the old door.
      application = isinstance(value, list) and value and isinstance(value[0], CurryNodeInfo)
      if isinstance(value, list) and any(isinstance(v, expressions.unboxed) for v in value):
        application = True
      if not application:
        args = (term(interp, value),)
  return args


def _text(value):
  if isinstance(value, goals.Goal):
    return value.text or _text(value.expr)
  if isinstance(value, backends.Node):
    # A raw graph can be cyclic or enormous. Its head names the old door.
    return value.info.name
  try:
    return str(value)
  except RecursionError:
    return '<term>'


def _under_io(typeexpr):
  if isinstance(typeexpr, fc.TCons) and typeexpr.name == IO and len(typeexpr.args) == 1:
    return typeexpr.args[0]
  return typeexpr


class _Variables:
  '''Resolve runtime variables to their Python identities within one run.'''
  def __init__(self, interp, source):
    self.interp = interp
    self.source = source
    self.foreign = {}

  def __call__(self, node):
    vid = inspect.get_freevar_id(node)
    for var in self.source:
      held = var._marker._shared(self.interp)
      if held is not None:
        held = _follow(held)
        if inspect.isa_freevar(held) and inspect.get_freevar_id(held) == vid:
          return var
    if vid not in self.foreign:
      var = Var(self.interp)
      var._marker._share(self.interp, node)
      self.foreign[vid] = var
    return self.foreign[vid]


def _converter(interp, typeexpr, variables):
  to_python = conversions.ToPython(variable=_Variables(interp, variables), interp=interp)
  return lambda ip, value: to_python(value, typeexpr=_under_io(typeexpr))


def _run(interp, goal, convert, answer=False):
  # Creating a runtime state can inspect the root. Defer it until next().
  interp.backend.before_evaluation(interp)
  values = goal.evaluate(interp)
  try:
    for value in values:
      bindings = Bindings() if answer else None
      if convert is not None:
        value = convert(interp, value)
      yield Answer(value, bindings) if answer else value
  except FileNotFoundError as error:
    from ..exceptions import CurryFileNotFoundError
    if isinstance(error, CurryFileNotFoundError):
      raise
    exc = CurryFileNotFoundError('i/o error: %s: %s' % (error.strerror, error.filename))
    exc.filename = error.filename
    raise exc from None
  except OSError as error:
    from ..exceptions import CurryIOError
    if isinstance(error, CurryIOError):
      raise
    raise CurryIOError('i/o error: %s' % error.strerror) from None
  except RecursionError as error:
    from ..exceptions import StackLimitError
    raise StackLimitError(str(error)) from None
  finally:
    values.close()


def eval(interp, *args, **kwds):
  """Return the converted values of an internal goal description."""
  return _evaluate(interp, args, kwds, raw=False)


def eval_nodes(interp, *args, **kwds):
  """Return runtime nodes for internal callers."""
  return _evaluate(interp, args, kwds, raw=True)


def _evaluate(interp, args, kwds, raw):
  args = _arguments(interp, args, kwds)
  variables = [v for v in walk_forms(args) if isinstance(v, Var)]
  goal = goals.make_goal(interp, args, exprtype=kwds.pop('exprtype', None), anchors=kwds)
  text = goal.text or _text(args[0])
  convert = None if raw else _converter(interp, expressions.result_type(interp, goal.expr), variables)
  return Results(_run(interp, goal, convert), text)


def solve(interp, goal):
  '''Return a Results of Answer(value, bindings), reporting every named Var.'''
  args = _arguments(interp, (goal,), {})
  value = args[0]
  variables = tuple(named_vars(value).values())
  all_vars = [v for v in walk_forms(value) if isinstance(v, Var)]
  if variables:
    bindings = ()
    for var in reversed(variables):
      bindings = (var, bindings)
    goal = goals.make_goal(interp, ((value, bindings),))
    convert = _converter(interp, expressions.result_type(interp, goal.expr), all_vars)
    def answers():
      values = _run(interp, goal, convert)
      try:
        for result, bindings in values:
          parts = []
          for var in variables:
            part, bindings = bindings
            parts.append((var.name, part))
          yield Answer(result, Bindings(parts, variables))
      finally:
        values.close()
    values = answers()
  else:
    goal = goals.make_goal(interp, args)
    convert = _converter(interp, expressions.result_type(interp, goal.expr), all_vars)
    values = _run(interp, goal, convert, answer=True)
  return Results(values, str(value))


def _yield_type(interp, printer):
  # The printer supplies the type information its dictionaries retain.
  from ..typecheck.stream import output_type
  return output_type(interp, printer)


def _print_yield(interp, event):
  value, printer = event.successors
  text = interp.expr(interp.symbol('Prelude.apply'), printer, value)
  text = interp.expr(interp.symbol('Prelude.$##'),
      interp.symbol('Prelude.returnIO'), text)
  typeexpr = expressions.result_type(interp, text)
  values = eval_nodes(interp, text)
  try:
    line = conversions.ToPython(interp=interp)(next(values), typeexpr=typeexpr)
    print(line, flush=True)
    interp._stream_outputs = getattr(interp, '_stream_outputs', 0) + 1
  finally:
    values.close()


def stream(interp, action):
  '''The output events of an IO goal, with its final value as the result.'''
  if interp.flags['backend'] != 'cxx':
    raise NotImplementedError('curry.stream requires the C++ backend')
  args = _arguments(interp, (action,), {})
  variables = [v for v in walk_forms(args) if isinstance(v, Var)]
  goal = goals.make_goal(interp, args)
  typeexpr = expressions.result_type(interp, goal.expr)
  if isinstance(typeexpr, fc.TVar):
    goal = goals.make_goal(interp, args, exprtype='IO a')
    typeexpr = expressions.result_type(interp, goal.expr)
  if not isinstance(typeexpr, fc.TCons) or typeexpr.name != IO:
    from ..exceptions import CurryTypeError
    raise CurryTypeError('curry.stream needs an IO action; use curry.eval for a pure goal')
  # Normalize the action on behalf of a monadic function. This applies the
  # ordinary I/O choice rule at the root too, and to the action's result.
  goal._expr = interp.expr(interp.symbol('Prelude.$!!'),
      interp.symbol('Prelude.returnIO'), goal.expr)
  convert = conversions.ToPython(variable=_Variables(interp, variables), interp=interp)
  def run():
    interp.backend.before_evaluation(interp)
    expr, goal._expr = goal._expr, None
    rts = interp.backend.create_evaluation_rts(interp, expr)
    del expr
    events = interp._evaluation_totals.track(rts, rts.generate_events())
    try:
      for output, value in events:
        if output:
          item, printer = value.successors
          yield convert(item, typeexpr=_yield_type(interp, printer))
        else:
          return convert(value, typeexpr=typeexpr)
    finally:
      try:
        events.close()
      finally:
        # A retained exception can keep these frames and the state alive.
        # Release its queue independently of the Python object's lifetime.
        rts.close()
        interp.backend.after_evaluation(interp)
  return Stream(run())

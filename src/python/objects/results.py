'''The lazy results of an evaluation and its variable bindings.'''

from collections.abc import Iterator, Mapping
from typing import NamedTuple
import functools, threading

def _consuming(function):
  @functools.wraps(function)
  def call(self, *args, **kwds):
    with self._lock:
      if self._busy:
        raise ValueError('generator already executing')
      self._busy = True
    try:
      return function(self, *args, **kwds)
    finally:
      with self._lock:
        self._busy = False
  return call

from ..exceptions import NoValueError, ManyValuesError, SuspensionError

class Results(Iterator):
  '''A lazy search. Closing it releases the evaluation.'''
  def __init__(self, values, text):
    self._lock = threading.Lock()
    self._busy = False
    self._values = values
    self._text = text

  def __iter__(self):
    return self

  @_consuming
  def __next__(self):
    if self._values is None:
      raise StopIteration
    try:
      return next(self._values)
    except SuspensionError:
      self._close()
      raise SuspensionError('Evaluation suspended: ' + self._text) from None
    except BaseException:
      self._close()
      raise

  def one(self):
    try:
      first = next(self)
    except StopIteration:
      raise NoValueError('No value found: %s' % self._text) from None
    try:
      second = next(self)
    except StopIteration:
      return first
    self.close()
    from .. import show
    raise ManyValuesError('more than one value: %s has %s and %s'
        % (self._text, show(first), show(second)))

  @_consuming
  def close(self):
    self._close()

  def _close(self):
    values, self._values = self._values, None
    if values is not None:
      close = getattr(values, 'close', None)
      if close is not None:
        close()

  def __enter__(self):
    return self

  def __exit__(self, *exc):
    self.close()

  def __repr__(self):
    return '<Results of %s%s>' % (self._text,
        ', closed' if self._values is None else '')

class Stream(Iterator):
  '''The ordered values yielded by an I/O action; result is set at its end.'''
  def __init__(self, values):
    self._lock = threading.Lock()
    self._busy = False
    self._values = values
    self.result = None

  def __iter__(self):
    return self

  @_consuming
  def __next__(self):
    if self._values is None:
      raise StopIteration(self.result)
    try:
      return next(self._values)
    except StopIteration as done:
      self.result = done.value
      self._close()
      raise
    except BaseException:
      self._close()
      raise

  @_consuming
  def close(self):
    self._close()

  def _close(self):
    values, self._values = self._values, None
    if values is not None:
      values.close()

def _key(value):
  from .. import backends
  if isinstance(value, backends.Node):
    # Raw nodes compare structurally but still hash by identity.
    return ('node',)
  if isinstance(value, (list, tuple)):
    return tuple(map(_key, value))
  return value

class Bindings(Mapping):
  '''Bindings in occurrence order, indexed by name, display name or Var.'''
  def __init__(self, items=(), variables=()):
    from .termshow import Context, show
    variables = tuple(variables)
    context = Context()
    context.used.update(var.name for var in variables if var.name is not None)
    self._variables = {var: show(var, context=context) for var in variables}
    self._items = {self._variables.get(key, key): value for key, value in dict(items).items()}

  def __getitem__(self, key):
    from .terms import Var
    if isinstance(key, Var):
      try:
        key = self._variables[key]
      except KeyError:
        raise KeyError(key) from None
    return self._items[key]

  def __iter__(self):
    return iter(self._items)

  def __len__(self):
    return len(self._items)

  def __hash__(self):
    return hash(frozenset((name, _key(value)) for name, value in self.items()))

  def _context(self, value=()):
    from .termshow import Context, _used_names
    context = Context()
    context.used.update(self._items)
    context.used.update(_used_names((value, tuple(self.values()))))
    context.variables.update((id(var), name) for var, name in self._variables.items())
    return context

  def _show(self, context):
    from .termshow import show
    return '{%s}' % ', '.join('%s=%s' % (name, show(value, context=context))
        for name, value in self.items())

  def __str__(self):
    return self._show(self._context())

  __repr__ = __str__

class Answer(NamedTuple):
  '''A value and its bindings. Its text is the REPL's answer line.'''
  value: object
  bindings: Bindings

  def __str__(self):
    from .termshow import show
    context = self.bindings._context(self.value)
    bindings = self.bindings._show(context)
    value = show(self.value, context=context)
    return '%s %s' % (bindings, value) if self.bindings else value

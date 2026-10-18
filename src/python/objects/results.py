'''The lazy results of an evaluation and its named bindings.'''

from collections.abc import Iterator, Mapping
from typing import NamedTuple
from ..exceptions import NoValueError, ManyValuesError, SuspensionError

class Results(Iterator):
  '''A lazy search. Closing it releases the evaluation.'''
  def __init__(self, values, text):
    self._values = values
    self._text = text

  def __iter__(self):
    return self

  def __next__(self):
    if self._values is None:
      raise StopIteration
    try:
      return next(self._values)
    except SuspensionError:
      self.close()
      raise SuspensionError('Evaluation suspended: ' + self._text) from None
    except BaseException:
      self.close()
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

  def close(self):
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
    self._values = values
    self.result = None

  def __iter__(self):
    return self

  def __next__(self):
    if self._values is None:
      raise StopIteration(self.result)
    try:
      return next(self._values)
    except StopIteration as done:
      self.result = done.value
      self.close()
      raise
    except BaseException:
      self.close()
      raise

  def close(self):
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
  '''An answer's bindings, in occurrence order, indexed by name or Var.'''
  def __init__(self, items=(), variables=()):
    self._items = dict(items)
    self._variables = {var: var.name for var in variables}

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

  def __str__(self):
    from .. import show
    return '{%s}' % ', '.join('%s=%s' % (name, show(value))
        for name, value in self.items())

  __repr__ = __str__

class Answer(NamedTuple):
  '''A value and its bindings. Its text is the REPL's answer line.'''
  value: object
  bindings: Bindings

  def __str__(self):
    from .. import show
    value = show(self.value)
    return '%s %s' % (self.bindings, value) if self.bindings else value

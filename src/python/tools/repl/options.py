'''The REPL uses the session's flag names and validator.'''

from ...interpreter.flags import FLAG_INFO, _convert, check_flags
import collections, importlib

curry = importlib.import_module(__package__.split('.')[0])


class OptionSpec(collections.namedtuple('_OptionSpec', 'name spec')):
  @property
  def isbool(self):
    return self.spec is bool


class Options:
  def __init__(self, repl=None):
    self.repl = repl
    self.values = dict(curry.flags)

  def __setitem__(self, name, value):
    # Unknown names go through the same validator as reset.
    if name not in FLAG_INFO:
      check_flags({name: value})
    if isinstance(value, str):
      converted = _convert(value, FLAG_INFO[name][0])
      if converted is not NotImplemented:
        value = converted
    check_flags({name: value})
    if self.repl is None:
      self.values[name] = value
    else:
      self.repl.set_flags(**{name: value})

  def __getitem__(self, name):
    return self.values[name]

  @classmethod
  def names(cls):
    return FLAG_INFO.keys()

  @classmethod
  def usage(cls, name, indent=0):
    description = ('The backend of the session.  Setting it reloads the '
        'interpreter and the loaded module.' if name == 'backend'
        else 'The %s session flag.' % name)
    return '%s%s - %s' % (' ' * indent, name, description)

  def state(self, name):
    return name, self.values[name], OptionSpec(name, FLAG_INFO[name][0])

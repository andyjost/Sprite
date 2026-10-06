from .resolve import resolve
import collections, importlib
curry = importlib.import_module(__package__[:__package__.find('.')])

BACKENDS = ('py', 'cxx')

class OptionSpec(collections.namedtuple(
    '_OptionSpec', ('name', 'type', 'default', 'argnames', 'setter', 'doc')
  )):
  @property
  def setter(self):
    sup = super(OptionSpec, self)
    return sup.setter if sup.setter else self._defaultsetter
  def _defaultsetter(self, inst, value):
    if issubclass(self.type, bool) and isinstance(value, str):
      arg = str(value).lower()
      if arg in ['true', 'on', 'yes']:
        value = True
      elif arg in ['false', 'off', 'no']:
        value = False
      else:
        try:
          value = int(value)
        except:
          raise ValueError("Invalid Boolean value: {0!r}.".format(value))
    inst.values[self.name] = self.type(value)
  def description(self, indent=0, w1=0):
    return '{0}{1}  - {2}'.format(
        ' ' * indent
      , self.name.ljust(w1)
      , self.doc
      )
  @property
  def isbool(self):
    return self.type is bool


def set_backend(inst, value):
  '''
  The setter of the option ``backend``: reloads the interpreter with the
  backend and loads the module of the session again (REPL.switch_backend,
  which records the value once the interpreter runs on the backend).
  '''
  value = str(value)
  if value not in BACKENDS:
    raise ValueError(
        'Invalid backend: %r.  Expected one of %s.'
      % (value, ', '.join(repr(b) for b in BACKENDS))
      )
  if inst.repl is None:
    inst.values['backend'] = value
  else:
    inst.repl.switch_backend(value)


class Options(object):
  OPTIONS = {
      name: OptionSpec(name, *args) for name,args in {
          'backend' : (str, None, ['py|cxx'], set_backend,
              'The backend of the session, py or cxx.  Setting it reloads '
              'the interpreter and the loaded module.')
        , 'internal-error-details' : (bool, False, [], None,
              'Show detailed information about internal errors.')
        }.items()
    }
  W1 = 1 + max(len(name) for name in OPTIONS)
  def __init__(self, repl=None):
    # The REPL that owns the options, for the setters that act on the
    # session; None in a bare Options object.
    self.repl = repl
    self.values = {
        option.name: option.default for option in self.OPTIONS.values()
      }
    # The backend of the interpreter at the start of the session.
    self.values['backend'] = curry.flags['backend']
  def __setitem__(self, name, value):
    name = resolve(name, self.OPTIONS.keys(), 'option')
    self.OPTIONS[name].setter(self, value)
  def __getitem__(self, name):
    name = resolve(name, self.OPTIONS.keys(), 'option')
    return self.values[name]
  @classmethod
  def names(cls):
    return cls.OPTIONS.keys()
  @classmethod
  def usage(cls, name, indent=0):
    return cls.OPTIONS[name].description(indent, cls.W1)
  def state(self, name):
    name = resolve(name, self.OPTIONS.keys(), 'option')
    return name, self.values[name], self.OPTIONS[name]



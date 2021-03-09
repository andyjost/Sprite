from .resolve import resolve
import collections

class OptionSpec(collections.namedtuple(
    '_OptionSpec', ('name', 'type', 'default', 'argnames', 'setter', 'doc')
  )):
  @property
  def setter(self):
    sup = super(OptionSpec, self)
    return sup.setter if sup.setter else self._defaultsetter
  def _defaultsetter(self, inst, value):
    if issubclass(self.type, bool) and isinstance(value, (str, unicode)):
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


class Options(object):
  OPTIONS = {
      name: OptionSpec(name, *args) for name,args in {
          'internal-error-details' : (bool, False, [], None,
              'Show detailed information about internal errors.')
        }.items()
    }
  W1 = 1 + max(
      len(option.type.__name__) + len(' '.join(option.argnames))
          for option in OPTIONS.values()
    )
  def __init__(self):
    self.values = {
        option.name: option.default for option in self.OPTIONS.values()
      }
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



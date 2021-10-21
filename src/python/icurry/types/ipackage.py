from .imodule import IPackageOrModule
from . import inspect
from .. import utility
from .isymbol import ISymbol

class IPackage(IPackageOrModule):
  '''
  A container for subpackages and/or modules.
  '''
  def __init__(self, fullname, submodules, **kwds):
    self.fullname = fullname
    ISymbol.__init__(self, **kwds)
    self.submodules = {}
    for module in submodules:
      self.insert(module)

  _fields_ = 'fullname', 'submodules'

  @property
  def children(self):
    return self.submodules.values()

  def __getitem__(self, key):
    return self.submodules[key]

  def __contains__(self, key):
    return key in self.submodules

  def __iter__(self):
    return self.submodules.iterkeys()

  def insert(self, submodule):
    assert inspect.isa_module_or_package(submodule)
    assert submodule.fullname.startswith(self.fullname)
    shortname = submodule.fullname[len(self.fullname)+1:]
    key,_ = utility.splitname(shortname)
    self.submodules[key] = submodule
    submodule.setparent(self)

  def __delitem__(self, name):
    del self.submodules[name]

  def merge(self, extern, export):
    '''
    Moves the symbols specified in ``export`` from ``extern`` into this module.
    Takes ownership of the submodules by setting ``parent``.  Because of this,
    the submodules are deleted from ``extern``.
    '''
    assert isinstance(extern, IPackage)
    for name in export:
      if name not in extern:
        raise TypeError(
            'cannot import %r from module %r' % (name, extern.fullname)
          )
      if name in self and self[name] is not extern[name]:
        raise TypeError(
            'importing %r into %r would clobber a symbol'
                % (name, self.fullname)
          )
      self.insert(extern.submodules.pop(name))

  def __str__(self):
    return '\n'.join(
        [
            'Package:'
          , '--------'
          , '  name: %s' % self.name
          , '  fullname: %s' % self.fullname
          , '  keys: %s' % sorted(self.submodules.keys())
          , ''
          , '  submodules:'
          , '  -----------'
          ]
      + [   '    ' + line for key in sorted(self)
                          for line in str(self[key]).split('\n')
          ]
      )


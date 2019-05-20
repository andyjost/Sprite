from abc import ABCMeta
from collections import Mapping, namedtuple, OrderedDict, Sequence
from .utility.proptree import proptree
from .utility.visitation import dispatch
import json
import logging
import re
import weakref

logger = logging.getLogger(__name__)

class _Base(object):
  # Make objects comparable by their contents.
  def __eq__(lhs, rhs):
    if rhs is None:
      return False
    if type(lhs) != type(rhs):
      return False

    # Compare dicts, ignoring parents.
    d_lhs = {k:v for k,v in lhs.__dict__.iteritems() if k != 'parent'}
    d_rhs = {k:v for k,v in rhs.__dict__.iteritems() if k != 'parent'}
    return d_lhs == d_rhs

  def __ne__(lhs, rhs):
    return not (lhs == rhs)

  def __hash__(self):
    return hash(tuple(sorted(
        (k,v) for k,v in self.__dict__.iteritems() if k != 'parent'
      )))

  @classmethod
  def construct(cls, arg, parent):
    '''Construct an object of the specified type and specify its parent.'''
    obj = arg if isinstance(arg, cls) else cls(*arg)
    return obj.setparent(parent)

  # Make pickling safe.  Attribute parent is a weakref, which cannot be
  # pickled.  Just convert it to a normal ref and back.
  def __getstate__(self):
    state = self.__dict__.copy()
    if 'parent' in state:
      state['parent'] = self.parent()
    return state

  def __setstate__(self, state):
    self.__dict__ = state.copy()
    if getattr(self, 'parent', None) is not None:
      self.parent = weakref.ref(self.parent)


class IName(str):
  def __new__(cls, arg1, arg2=None, modulename=None):
    if arg2 is None:
      ident = arg1
      parts = ident.split('.')
      module, basename = parts[0], '.'.join(parts[1:])
      if basename == '':
        module, basename = None, module
    else:
      module, basename = arg1, arg2
      ident = '.'.join([arg1, arg2])
    self = str.__new__(cls, ident)
    self.module = module
    self.basename = basename
    return self.setmodule(modulename)

  def setmodule(self, modulename):
    if modulename is None or self.module == modulename:
      return self
    elif self.module is None:
      return IName(modulename, self.basename)
    else:
      raise ValueError(
          'expected module name "%s", got "%s"' % (self.module, modulename)
        )


def _build_symboltable(imodule, data, value_type):
  '''
  Builds an ordered mapping from ``IName`` to ``value_type`` where
  ``value_type`` also has the name embedded.  Sets the module name for all
  items.

  Parameters:
  -----------
    ``imodule``    The IModule instance that owns the symbols.
    ``data``       A mapping or sequence of pairs used to create the table.
    ``value_type`` The mapping value type.  Must be a subclass of ``_Base``.
  '''
  construct = lambda obj: value_type.construct(obj, parent=imodule)
  if isinstance(data, Mapping):
    data = OrderedDict(
        (IName(k, modulename=imodule.name), construct(v))
            for k,v in data.items()
      )
  else:
    data = OrderedDict((v.ident, v) for v in (construct(v) for v in data))
  assert all(isinstance(v, value_type) for v in data.values())
  assert all(k == v.ident for k,v in data.items())
  return data

class IModule(_Base):
  def __init__(self, name, imports, types, functions, filename=None):
    '''
    Parameters:
    -----------
      name        The module name.
      imports     A list of imported module names.
      types       A mapping or sequence of pairs: IName -> [IConstructor].
      functions   A sequence of IFunctions, or a mapping or sequence of pairs:
                  IName -> IFunction.
    '''
    self.name = str(name)
    self.imports = tuple(str(x) for x in imports)
    self.types = _build_symboltable(self, types, IType)
    self.functions = _build_symboltable(self, functions, IFunction)
    self.filename = filename
  def __str__(self):
    return '\n'.join(
        [
            'Module:'
          , '-------'
          , '  name: %s' % self.name
          , '  imports: %s' % ', '.join(self.imports)
          , ''
          , '  types:'
          , '  ------'
          ]
      + [   '    ' + str(ty) for ty in self.types.values() ]
      + [
            ''
          , '  functions:'
          , '  ----------'
          ]
      + [   '    ' + line for func in self.functions.values()
                          for line in str(func).split('\n')
          ]
      )

  def __repr__(self):
    return 'IModule(name=%s, imports=%s, types=%s, functions=%s)' % (
        repr(self.name), repr(self.imports), repr(self.types)
      , repr(self.functions)
      )

  def merge(self, extern, export):
    '''
    Copies the symbols specified in ``export`` from ``extern`` into this
    module.
    '''
    for name in export:
      ident = IName(name, modulename=self.name)
      found = 0
      for to,from_ in zip(*[[m.types, m.functions] for m in [self, extern]]):
        try:
          to[ident] = from_[ident]
        except KeyError:
          pass
        else:
          found += 1
      if not found:
        raise TypeError('exported symbol "%s" not found' % ident)

class IType(_Base, Sequence):
  def __init__(self, ident, constructors, metadata={}):
    self.ident = IName(ident)
    self.constructors = tuple(
        arg if isinstance(arg, IConstructor) else IConstructor(*arg)
            for arg in constructors
      )
    self.metadata = proptree(metadata)

  def setparent(self, parent):
    assert isinstance(parent, IModule)
    self.parent = weakref.ref(parent)
    self.ident = IName(self.ident, modulename=parent.name)
    for constructor in self.constructors:
      constructor.setparent(self)
    return self

  def __iter__(self):
    return iter(self.constructors)

  def __len__(self):
    return len(self.constructors)

  def __getitem__(self, i):
    return self.constructors[i]

  def __str__(self):
    return '%s = %s' % (self.ident.basename, ' | '.join(map(str, self.constructors)))

  def __repr__(self):
    return 'IType(ident=%s, constructors=%s)' % (
        repr(self.ident), repr(list(self.constructors))
      )

class IConstructor(_Base):
  def __init__(self, ident, arity, metadata={}):
    assert arity >= 0
    self.ident = IName(ident)
    self.arity = int(arity)
    self.metadata = proptree(metadata)

  def setparent(self, parent):
    assert isinstance(parent, IType)
    self.parent = weakref.ref(parent)
    self.ident = IName(self.ident, modulename=parent.parent().name)
    return self

  @property
  def index(self):
    return self.parent().index(self)

  def __str__(self):
    return self.ident.basename

  def __repr__(self):
    return 'IConstructor(ident=%s, arity=%d)' % (repr(self.ident), self.arity)

class IFunction(_Base):
  def __init__(self, ident, arity, code=[], metadata={}):
    assert arity >= 0
    self.ident = IName(ident)
    self.arity = int(arity)
    self.code = tuple(code)
    self.metadata = proptree(metadata)

  def setparent(self, parent):
    assert isinstance(parent, IModule)
    self.parent = weakref.ref(parent)
    self.ident = IName(self.ident, modulename=parent.name)
    return self

  def __str__(self):
    return '\n'.join(
        [self.ident.basename + ':']
      + ['  %s' % line for line in '\n'.join(map(str, self.code)).split('\n')]
      )

  def __repr__(self):
    return 'IFunction(ident=%s, arity=%d, code=%s)' % (
        repr(self.ident), self.arity, repr(self.code)
      )

class Successor(namedtuple('Successor', ['headsymbol', 'position'])):
  def __str__(self):
    return str(self.position)

class ILhs(_Base):
  def __init__(self, index):
    self.index = Successor(*index)
  def __str__(self):
    return 'LHS[%s]' % str(self.index)
  def __repr__(self):
    return 'ILhs(index=%s)' % repr(self.index)

class IVar(_Base):
  def __init__(self, vid, index):
    assert vid >= 0
    self.vid = int(vid)
    self.index = Successor(*index)
  def __str__(self):
    return '%s[%s]' % (Reference(self.vid), self.index)
  def __repr__(self):
    return 'IVar(vid=%d, index=%s)' % (self.vid, repr(self.index))

class IBind(_Base):
  def __str__(self):
    return 'IBind'
  def __repr__(self):
    return 'IBind()'

class IFree(_Base):
  def __str__(self):
    return 'IFree'
  def __repr__(self):
    return 'IFree()'

class VarScope(object):
  __metaclass__ = ABCMeta
VarScope.register(ILhs)
VarScope.register(IVar)
VarScope.register(IBind)
VarScope.register(IFree)

class BuiltinVariant(object):
  __metaclass__ = ABCMeta
BuiltinVariant.register(int)
BuiltinVariant.register(float)
BuiltinVariant.register(str)

class Variable(_Base):
  def __init__(self, vid, scope):
    assert vid >= 0
    assert isinstance(scope, VarScope)
    self.vid = int(vid)
    self.scope = scope
  def __str__(self):
    return '$%d <- %s' % (self.vid, str(self.scope))
  def __repr__(self):
    return 'Variable(vid=%d, scope=%s)' % (self.vid, repr(self.scope))

class Exempt(_Base):
  def __str__(self):
    return 'Exempt'
  def __repr__(self):
    return 'Exempt()'

class Reference(_Base):
  def __init__(self, vid):
    assert vid >= 0
    self.vid = int(vid)
  def __str__(self):
    return '$%d' % self.vid
  def __repr__(self):
    return 'Reference(vid=%d)' % self.vid

def _fmtTerm(term):
  text = str(term)
  return '(%s)' % text if len(text.split(' ')) > 1 else text

class Applic(_Base):
  def __init__(self, ident, args=[]):
    self.ident = IName(ident)
    self.args = tuple(args)
    # Special case for Float.  The JSON generator always uses a general number
    # representation, so something like (Float 1.0) receives an int.
    if self.ident == "Prelude.Float":
      self.args = tuple(map(float, self.args))
  def __str__(self):
    args = [self.ident] + [_fmtTerm(term) for term in self.args]
    return '(' + ' '.join(args) + ')'
  def __repr__(self):
    return 'Applic(ident=%s, args=%s)' % (repr(self.ident), repr(self.args))

class PartApplic(_Base):
  def __init__(self, missing, expr):
    assert missing >= 0
    # assert isinstance(expr, object)
    self.missing = int(missing)
    self.expr = expr
  def __str__(self):
    return '(%s)' % self.expr
  def __repr__(self):
    return 'PartApplic(missing=%s, expr=%s)' % (self.missing, repr(self.expr))

class IOr(_Base):
  def __init__(self, lhs, rhs):
    # assert all(isinstance(x, object) for x in [lhs, rhs])
    self.lhs = lhs
    self.rhs = rhs
  def __str__(self):
    return '%s ? %s' % (self.lhs, self.rhs)
  def __repr__(self):
    return 'IOr(lhs=%s, rhs=%s)' % (repr(self.lhs), repr(self.rhs))

class Expression(object):
  __metaclass__ = ABCMeta
Expression.register(int)
Expression.register(float)
Expression.register(str)
Expression.register(Exempt)
Expression.register(Reference)
Expression.register(Applic)
Expression.register(PartApplic)
Expression.register(IOr)

class IExternal(_Base):
  def __init__(self, ident):
    self.ident = str(ident)
  def __str__(self):
    return 'extern(%s)' % self.ident
  def __repr__(self):
    return 'IExternal(ident=%s)' % repr(self.ident)

class Comment(_Base):
  def __init__(self, text):
    self.text = str(text)
  def __str__(self):
    return '-- %s' % self.text
  def __repr__(self):
    return 'Comment(text=%s)' % repr(self.text)

class Declare(_Base):
  def __init__(self, var):
    assert isinstance(var, Variable)
    self.var = var
  def __str__(self):
    return str(self.var)
  def __repr__(self):
    return 'Declare(var=%s)' % repr(self.var)

class Assign(_Base):
  def __init__(self, vid, expr):
    assert vid >= 0
    assert isinstance(expr, Expression)
    self.vid = int(vid)
    self.expr = expr
  def __str__(self):
    return '$%d = %s' % (self.vid, repr(self.expr))
  def __repr__(self):
    return 'Assign(vid=%d, expr=%s)' % (self.vid, repr(self.expr))

class Fill(_Base):
  def __init__(self, v1, path, v2):
    assert v1 >= 0
    assert v2 >= 0
    self.v1 = int(v1)
    self.path = tuple(path)
    assert all(isinstance(p, Successor) for p in self.path)
    self.v2 = int(v2)
  def __str__(self):
    return '%s[%s] <- %s' % (Reference(self.v1), self.path, Reference(self.v2))
  def __repr__(self):
    return 'Fill(v1=%s, path=%s, v2=%s)' % (
        repr(self.v1), repr(self.path), repr(self.v2)
      )

class Return(_Base):
  def __init__(self, expr):
    assert isinstance(expr, Expression)
    self.expr = expr
  def __str__(self):
    return 'return %s' % self.expr
  def __repr__(self):
    return 'Return(expr=%s)' % repr(self.expr)

class _XTable(_Base):
  def __str__(self):
    head = 'case %s of ' % str(self.expr)
    patlen = max(len(pat) for pat in map(str, self.switch))
    fmt = '%%-%ds -> %%s' % patlen
    indent = '\n' + (' ' * len(head))
    indent2 = '\n' + (' ' * (len(head) + len(' -> ') + patlen))
    body = indent.join(
        fmt % (str(pat), indent2.join(map(str,expr)))
            for pat,expr in self.switch.iteritems()
      )
    return head + body
  def __repr__(self):
    return '%s(counter=%d, isflex=%s, expr=%s, switch=%s)' % (
        self.__class__.__name__, self.counter, repr(self.isflex), repr(self.expr)
      , repr(self.switch)
      )

class ATable(_XTable):
  '''
  A case table over constructors.

  The meaning of flexible/rigid (it applies ot both a case and a function) is
  whether a variable can be instantiated by a pattern.  Consider the following
  program:

    mynot x  = case x of {True -> False; False -> True}
    main = mynot x where x free

  Since the case is rigid the evaluation of main suspends.

  However, if you replace "case" with "fcase" the evaluation of main produces
  both False and True because x is bound to True and False, respectively.
  '''
  def __init__(self, counter, isflex, expr, switch):
    assert counter >= 0
    assert isinstance(expr, Expression)
    self.counter = int(counter)
    self.isflex = bool(isflex)
    self.expr = expr
    self.switch = dict(switch)
    self.switch = dict(
        [k.ident if hasattr(k,'ident') else IName(k), v]
            for k,v in self.switch.iteritems()
      )
    assert all(
        isinstance(k,IName) and all(isinstance(s,Statement) for s in v)
            for k,v in self.switch.iteritems()
      )

class BTable(_XTable):
  '''
  A case table over built-in values.

  ``isflex`` has the same meaning as for ``ATable``.
  '''
  def __init__(self, counter, isflex, expr, switch):
    assert counter >= 0
    assert isinstance(expr, Expression)
    self.counter = int(counter)
    self.isflex = bool(isflex)
    self.expr = expr
    self.switch = dict(switch)
    assert all(
        isinstance(k.ident, BuiltinVariant)
            and all(isinstance(s,Statement) for s in v)
            for k,v in self.switch.iteritems()
      )

class Statement(object):
  __metaclass__ = ABCMeta
Statement.register(IExternal)
Statement.register(Comment)
Statement.register(Declare)
Statement.register(Assign)
Statement.register(Fill)
Statement.register(Return)
Statement.register(ATable)
Statement.register(BTable)

@dispatch.on('arg')
def uni2str(arg):
  '''Convert unicode to str in a nested structure.'''
  return arg

@uni2str.when(unicode)
def uni2str(arg):
  return arg.encode('utf-8')

@uni2str.when(Sequence, no=(Successor,))
def uni2str(arg):
  return type(arg)(uni2str(x) for x in arg)

@uni2str.when(Mapping)
def uni2str(arg):
  return type(arg)((uni2str(k),uni2str(v)) for k,v in arg.items())

def _object_hook(kwds):
  cls = kwds.pop('__class__')
  return globals()[cls](**uni2str(kwds))

def get_decoder():
  return json.JSONDecoder(object_hook=_object_hook)

def parse(data, decoder=get_decoder()):
  '''Parse ICurry encoded as JSON.'''
  return decoder.decode(data)

def despace(data):
  '''Remove unnecessary spaces from JSON.'''
  # Remove all spaces not in a double-quoted string.
  return re.sub('("[^"]*")|\\s', lambda m: m.group(1), data)

@dispatch.on('arg')
def unbox(arg):
  '''Unapplies a built-in-type wrapper.'''
  raise TypeError('expected an Applic')

@unbox.when(Applic)
def unbox(applic):
  if applic.ident not in ['Prelude.' + s for s in ['Int', 'Float', 'Char']]:
    raise TypeError('expected an Int, Float, or Char')
  assert len(applic.args) == 1
  return applic.args[0]

@dispatch.on('arg')
def getmd(arg, extern, **kwds):
  '''
  Get metadata from an ICurry object

  Parameters:
  -----------
    ``arg``
      An instance of IConstructor, IFunction or IType.
    ``extern``
      An instance of IModule that provides external definitions.  If provided,
      this takes precedence over the metadata found in ``arg``.
    ``itype``
      Keyword only.  An instance of IType, used to resolve constructors.
      Required for IConstructor.

  Return:
  -------
  The metadata value, if found, or None otherwise.
  '''
  assert False

@getmd.when(IConstructor)
def getmd(icons, extern, itype):
  try:
    ctors = extern.types[itype.ident].constructors
    return next(c for c in ctors if c.ident == icons.ident).metadata
  except (AttributeError, KeyError, StopIteration):
    return icons.metadata

@getmd.when(IFunction)
def getmd(ifun, extern):
  try:
    return extern.functions[ifun.ident].metadata
  except (AttributeError, KeyError):
    return ifun.metadata

@getmd.when(IType)
def getmd(itype, extern):
  try:
    return extern.types[itype.ident].metadata
  except (AttributeError, KeyError):
    return itype.metadata


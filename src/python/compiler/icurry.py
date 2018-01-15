from abc import ABCMeta
from collections import OrderedDict, namedtuple
import json

class _Base(object):
  # Make objects comparable by their contents.
  def __eq__(lhs, rhs):
    if rhs is None:
      return False
    return type(lhs) == type(rhs) and lhs.__dict__ == rhs.__dict__
  def __ne__(lhs, rhs):
    return not (lhs == rhs)

class IName(str):
  def __new__(cls, arg1, arg2=None):
    if arg2 is None:
      ident = arg1
      parts = ident.split('.')
      module, basename = parts[0], '.'.join(parts[1:])
    else:
      module, basename = arg1, arg2
      ident = '.'.join(arg1, arg2)
    self = str.__new__(cls, ident)
    self.module = module
    self.basename = basename
    return self

class IModule(_Base):
  def __init__(self, name, imports, types, functions):
    self.name = str(name)
    self.imports = tuple(str(x) for x in imports)
    self.types = dict(types)
    self.types = {IName(k):tuple(v) for k,v in self.types.iteritems()}
    assert all(
        all(isinstance(ctor, IConstructor) for ctor in ctors)
            for ctors in self.types.values()
      )
    self.functions = tuple(functions)
    assert all(isinstance(x, IFunction) for x in self.functions)
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
      + ['    %s = %s' % (typename.basename, ' | '.join(map(str, ctors)))
              for typename,ctors in self.types.iteritems()
          ]
      + [
            ''
          , '  functions:'
          , '  ----------'
          ]
      + [   '    ' + line for func in self.functions
                          for line in str(func).split('\n')
          ]
      )

  def __repr__(self):
    return 'IModule(name=%s, imports=%s, types=%s, functions=%s)' % (
        repr(self.name), repr(self.imports), repr(self.types), repr(self.functions)
      )

class IConstructor(_Base):
  def __init__(self, ident, arity):
    assert arity >= 0
    self.ident = IName(ident)
    self.arity = int(arity)
  def __str__(self):
    return self.ident.basename
  def __repr__(self):
    return 'IConstructor(ident=%s, arity=%d)' % (repr(self.ident), self.arity)

class IFunction(_Base):
  def __init__(self, ident, arity, code):
    assert arity >= 0
    self.ident = IName(ident)
    self.arity = int(arity)
    self.code = tuple(code)
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
  def __init__(self, ident, args):
    self.ident = IName(ident)
    self.args = tuple(args)
    # assert all(isinstance(x, object) for x in self.args)
  def __str__(self):
    return '(%s %s)' % (
        self.ident, ' '.join(_fmtTerm(term) for term in self.args)
      )
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
  def __init__(self, name):
    self.name = str(name)
  def __str__(self):
    return 'extern(%s)' % self.name
  def __repr__(self):
    return 'IExternal(name=%s)' % repr(self.name)

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
    assert all(isinstance(p, VarScope) for p in self.path)
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
    patlen = max(len(pat) for pat in map(str, self.cases))
    fmt = '%%-%ds -> %%s' % patlen
    indent = '\n' + (' ' * len(head))
    indent2 = '\n' + (' ' * (len(head) + len(' -> ') + patlen))
    body = indent.join(
        fmt % (str(pat), indent2.join(map(str,expr)))
            for pat,expr in self.cases.iteritems()
      )
    return head + body
  def __repr__(self):
    return '%s(counter=%d, isflex=%s, expr=%s, cases=%s)' % (
        self.__class__.__name__, self.counter, repr(self.isflex), repr(self.expr)
      , repr(self.cases)
      )

class ATable(_XTable):
  def __init__(self, counter, isflex, expr, cases):
    assert counter >= 0
    assert isinstance(expr, Expression)
    self.counter = int(counter)
    self.isflex = bool(isflex)
    self.expr = expr
    self.cases = OrderedDict(cases)
    self.cases = OrderedDict(
        [k.ident if hasattr(k,'ident') else IName(k), v]
            for k,v in self.cases.iteritems()
      )
    assert all(
        isinstance(k,IName) and all(isinstance(s,Statement) for s in v)
            for k,v in self.cases.iteritems()
      )

class BTable(_XTable):
  def __init__(self, counter, isflex, expr, cases):
    assert counter >= 0
    assert isinstance(expr, Expression)
    self.counter = int(counter)
    self.isflex = bool(isflex)
    self.expr = expr
    self.cases = OrderedDict(cases)
    assert all(
        isinstance(k,BuiltinVariant) and all(isinstance(s,Statement) for s in v)
            for k,v in self.cases.iteritems()
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

def _object_hook(kwds):
  cls = kwds.pop('__class__')
  return globals()[cls](**kwds)

def get_decoder():
  return json.JSONDecoder(object_hook=_object_hook)

def parse(data, decoder=get_decoder()):
  '''Parse ICurry encoded as JSON.'''
  return decoder.decode(data)

def despace(data):
  '''Remove unnecessary spaces from JSON.'''
  # Remove all spaces not in a double-quoted string.
  return re.sub('("[^"]*")|\\s', lambda m: m.group(1), data)


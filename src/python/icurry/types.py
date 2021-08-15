from abc import ABCMeta
from collections import Iterator, OrderedDict, Mapping, Sequence
from ..utility.formatting import indent, wrapblock
from ..utility.proptree import proptree
from ..utility.visitation import dispatch
import logging
import weakref

logger = logging.getLogger(__name__)

PUBLIC = 0
PRIVATE = 1

class IObject(object):
  def __init__(self, metadata=None):
    if metadata is not None:
      self._metadata = proptree(metadata)

  @property
  def metadata(self):
    return getattr(self, '_metadata', {})

  def update_metadata(self, items):
    md = getattr(self.metadata, '_asdict', self.metadata)
    md.update(items)
    self._metadata = proptree(md)

  @property
  def children(self):
    return ()

  # Make objects comparable by their contents.
  def __eq__(lhs, rhs):
    if rhs is None:
      return False
    if type(lhs) != type(rhs):
      return False

    # Compare dicts, ignoring parents.
    d_lhs = {k:v for k,v in lhs.__dict__.iteritems() if k not in ('parent', 'metadata')}
    d_rhs = {k:v for k,v in rhs.__dict__.iteritems() if k not in ('parent', 'metadata')}
    return d_lhs == d_rhs

  def __ne__(lhs, rhs):
    return not (lhs == rhs)

  def __hash__(self):
    return hash(tuple(sorted(
        (k,v) for k,v in self.__dict__.iteritems() if k != 'parent'
      )))

  @property
  def fullname(self):
    mname = modulename(self)
    return mname if isinstance(self, IModule) else '%s.%s' % (mname, self.name)

  @property
  def modulename(self):
    return modulename(self)

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

IArity = int
IVarIndex = int
class IName(str): pass

class IInt(IObject):
  def __init__(self, value, **kwds):
    self.name = 'Prelude.Int'
    self.value = int(value)
    IObject.__init__(self, **kwds)
  def __str__(self):
    return '(%r)' % self.value # parens to suggest boxing
  def __repr__(self):
    return 'IInt(value=%r)' % self.value

class IChar(IObject):
  def __init__(self, value, **kwds):
    self.name = 'Prelude.Char'
    self.value = str(value)
    assert len(self.value) in (1,2) # Unicode can have length 2 in utf-8
    IObject.__init__(self, **kwds)
  def __str__(self):
    return '(%r)' % self.value # parens to suggest boxing
  def __repr__(self):
    return 'IChar(value=%r)' % self.value

class IFloat(IObject):
  def __init__(self, value, **kwds):
    self.name = 'Prelude.Float'
    self.value = float(value)
    IObject.__init__(self, **kwds)
  def __str__(self):
    return '(%r)' % self.value # parens to suggest boxing
  def __repr__(self):
    return 'IFloat(value=%r)' % self.value

class IUnboxedLiteral(IObject):
  __metaclass__ = ABCMeta
IUnboxedLiteral.register(int)
IUnboxedLiteral.register(str)
IUnboxedLiteral.register(float)
# An iterator is considered a fundamental data type so that Sprite does not try
# to reduce it.  This should always be the argument to an instance of
# Prelude._PyGenerator.
IUnboxedLiteral.register(Iterator)

class ILiteral(IObject):
  __metaclass__ = ABCMeta
ILiteral.register(IInt)
ILiteral.register(IChar)
ILiteral.register(IFloat)
ILiteral.register(IUnboxedLiteral)

def symboltable(parent, objs):
  return OrderedDict((v.name, v) for v in (v.setparent(parent) for v in objs))

class IModule(IObject):
  def __init__(self, name, imports, types, functions, filename=None, **kwds):
    '''
    Parameters:
    -----------
      name        The module name.
      imports     A list of imported module names.
      types       A mapping or sequence of pairs: str -> [IConstructor].
      functions   A sequence of IFunctions, or a mapping or sequence of pairs
                  from string to IFunction.
    '''
    self.name = str(name)
    self.imports = tuple(str(x) for x in imports)
    self.types = symboltable(self, types)
    self.functions = symboltable(self, functions)
    self.filename = str(filename) if filename is not None else None
    IObject.__init__(self, **kwds)

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
    return 'IModule(name=%r, filename=%r, imports=%r, types=%r, functions=%r)' % (
        self.name, self.filename, self.imports, self.types.values(), self.functions.values()
      )

  def merge(self, extern, export):
    '''
    Copies the symbols specified in ``export`` from ``extern`` into this
    module.
    '''
    for name in export:
      found = 0
      for to,from_ in zip(*[[m.types, m.functions] for m in [self, extern]]):
        try:
          to[name] = from_[name]
        except KeyError:
          pass
        else:
          found += 1
      if not found:
        raise TypeError('cannot import %r from module %r' % (name, extern.name))

IProg = IModule

class IConstructor(IObject):
  def __init__(self, name, arity, **kwds):
    assert arity >= 0
    self.name = iname(name)
    self.arity = IArity(arity)
    IObject.__init__(self, **kwds)

  def setparent(self, parent, index):
    assert isinstance(parent, IDataType)
    self.parent = weakref.ref(parent)
    self.index = index
    return self

  @property
  def typename(self):
    self.parent().fullname

  def __str__(self):
    return self.name + ' _' * self.arity

  def __repr__(self):
    return 'IConstructor(name=IName(%r), arity=%r)' % (self.name, self.arity)

class IDataType(IObject):
  def __init__(self, name, constructors, **kwds):
    self.name = iname(name)
    self.constructors = [ctor.setparent(self, i) for i,ctor in enumerate(constructors)]
    IObject.__init__(self, **kwds)

  def setparent(self, parent):
    assert isinstance(parent, IModule)
    self.parent = weakref.ref(parent)
    return self

  def __str__(self):
    return 'data %s = %s' % (self.name, ' | '.join(map(str, self.constructors)))

  def __repr__(self):
    return 'IDataType(name=IName(%r), constructors=%r)' % (self.name, self.constructors)
IType = IDataType

class IFunction(IObject):
  def __init__(self, name, arity, vis=None, needed=None, body=[], **kwds):
    assert arity >= 0
    self.name = iname(name)
    self.arity = IArity(arity)
    self.vis = PUBLIC if vis is None else vis
    # None means no info; [] means nothing needed.
    self.needed = None if needed is None else map(int, needed)
    self.body = body
    IObject.__init__(self, **kwds)

  def setparent(self, parent):
    assert isinstance(parent, IModule)
    self.parent = weakref.ref(parent)
    return self

  @property
  def is_private(self):
    return self.vis == PRIVATE

  def __str__(self):
    return '%s:\n%s' % (self.name, indent(self.body))

  def __repr__(self):
    return 'IFunction(name=IName(%r), arity=%r, vis=%r, needed=%r, body=%r)' % (
        self.name, self.arity, self.vis, self.needed, self.body
      )

class Public(IObject):
  def __repr__(self):
    return "PUBLIC"
  def __str__(self):
    return "Public"
PUBLIC = Public()

class Private(IObject):
  def __repr__(self):
    return "PRIVATE"
  def __str__(self):
    return "Private"
PRIVATE = Private()

class IVisibility(IObject):
  __metaclass__ = ABCMeta
IVisibility.register(Public)
IVisibility.register(Private)

class IExternal(IObject):
  def __init__(self, name, **kwds):
    self.name = str(name)
    IObject.__init__(self, **kwds)
  def __str__(self):
    return 'extern(%s)' % self.name
  def __repr__(self):
    return 'IExternal(name=%r)' % self.name

class IFuncBody(IObject):
  __metaclass__ = ABCMeta
  def __init__(self, block, **kwds):
    self.block = block
    IObject.__init__(self, **kwds)
  @property
  def children(self):
    return self.block,
  def __str__(self):
    return str(self.block)
  def __repr__(self):
    return 'IFuncBody(block=%r)' % self.block
IFuncBody.register(IExternal)

class IBlock(IObject):
  def __init__(self, vardecls, assigns, stmt, **kwds):
    self.vardecls = tuple(vardecls)
    self.assigns = tuple(assigns)
    self.stmt = stmt
    IObject.__init__(self, **kwds)
  @property
  def children(self):
    return self.vardecls + self.assigns + (self.stms,)
  def __str__(self):
    lines = map(str, self.vardecls)
    lines += map(str, self.assigns)
    lines.append(str(self.stmt))
    return '\n'.join(lines)
  def __repr__(self):
    return 'IBlock(vardecls=%r, assigns=%r, stmt=%r)' % (
        self.vardecls, self.assigns, self.stmt
      )

class IFreeDecl(IObject):
  def __init__(self, vid, **kwds):
    self.vid = vid
    IObject.__init__(self, **kwds)
  @property
  def lhs(self):
    return IVar(self.vid)
  def __str__(self):
    return 'free %s' % IVar(self.vid)
  def __repr__(self):
    return 'IFreeDecl(vid=%r)' % self.vid

class IVarDecl(IObject):
  __metaclass__ = ABCMeta
  def __init__(self, vid, **kwds):
    self.vid = vid
    IObject.__init__(self, **kwds)
  @property
  def lhs(self):
    return IVar(self.vid)
  def __str__(self):
    return 'var %s' % IVar(self.vid)
  def __repr__(self):
    return 'IVarDecl(vid=%r)' % self.vid
IVarDecl.register(IFreeDecl)

class IVarAssign(IObject):
  def __init__(self, vid, expr, **kwds):
    self.vid = vid
    self.expr = expr
    IObject.__init__(self, **kwds)
  @property
  def lhs(self):
    return IVar(self.vid)
  @property
  def rhs(self):
    return self.expr
  @property
  def children(self):
    return self.expr,
  def __str__(self):
    return '%s <- %s' % (IVar(self.vid), self.expr)
  def __repr__(self):
    return 'IVarAssign(vid=%r, expr=%r)' % (self.vid, self.expr)

class INodeAssign(IObject):
  def __init__(self, vid, path, expr, **kwds):
    self.vid = vid
    self.path = path
    self.expr = expr
    IObject.__init__(self, **kwds)
  @property
  def lhs(self):
    return IVarAccess(self.vid, self.path)
  @property
  def rhs(self):
    return self.expr
  @property
  def children(self):
    return self.expr,
  def __str__(self):
    return '%s <- %s' % (
        IVarAccess(self.vid, self.path), self.expr
      )
  def __repr__(self):
    return 'INodeAssign(vid=%r, path=%r, expr=%r)' % (
        self.vid, self.path, self.expr
      )

class IAssign(IObject):
  __metaclass__ = ABCMeta
IAssign.register(IVarAssign)
IAssign.register(INodeAssign)

class IExempt(IObject):
  def __str__(self):
    return 'exempt'
  def __repr__(self):
    return 'IExempt()'

class IReturn(IObject):
  def __init__(self, expr, **kwds):
    self.expr = expr
    IObject.__init__(self, **kwds)
  @property
  def children(self):
    return self.expr,
  def __str__(self):
    return 'return %s' % self.expr
  def __repr__(self):
    return 'IReturn(expr=%r)' % self.expr

class ICase(IObject):
  def __init__(self, vid, branches, **kwds):
    self.vid = vid
    self.branches = branches
    IObject.__init__(self, **kwds)
  @property
  def children(self):
    return self.branches
  def __str__(self):
    return 'case %s of\n%s' % (
        IVar(self.vid)
      , indent(self.branches)
      )
  def __repr__(self):
    return '%s(vid=%r, branches=%r)' % (
        type(self).__name__, self.vid, self.branches
      )

class ICaseCons(ICase): pass
class ICaseLit(ICase): pass

class IConsBranch(IObject):
  def __init__(self, name, arity, block, **kwds):
    self.name = name
    self.arity = arity
    self.block = block
    IObject.__init__(self, **kwds)
  @property
  def children(self):
    return self.block,
  def __str__(self):
    return '%s %s->%s' % (self.name, ''.join('_ ' * self.arity), wrapblock(self.block))
  def __repr__(self):
    return 'IConsBranch(name=%r, arity=%r, block=%r)' % (
        self.name, self.arity, self.block
      )

class ILitBranch(IObject):
  def __init__(self, lit, block, **kwds):
    self.lit = lit
    self.block = block
    IObject.__init__(self, **kwds)
  @property
  def children(self):
    return self.lit, self.block
  def __str__(self):
    return '%s ->%s' % (self.lit, wrapblock(self.block))
  def __repr__(self):
    return 'ILitBranch(lit=%r, block=%r)' % (self.lit, self.block)

class IStatement(IObject):
  __metaclass__ = ABCMeta
IStatement.register(IExempt)
IStatement.register(IReturn)
IStatement.register(ICaseCons)
IStatement.register(ICaseLit)
IStatement.register(IVarDecl)
IStatement.register(IAssign)
IStatement.register(IBlock)

class IVar(IObject):
  def __init__(self, vid, **kwds):
    self.vid = vid
    IObject.__init__(self, **kwds)
  def __str__(self):
    return '$%d' % self.vid
  def __repr__(self):
    return 'IVar(vid=%r)' % self.vid

class IVarAccess(IObject):
  def __init__(self, vid, path, **kwds):
    self.vid = vid
    self.path = path
    IObject.__init__(self, **kwds)
  @property
  def var(self):
    return IVar(self.vid)
  def __str__(self):
    return '%s[%s]' % (IVar(self.vid), '.'.join(map(str, self.path)))
  def __repr__(self):
    return 'IVarAccess(vid=%r, path=%r)' % (self.vid, self.path)

class ILit(IObject):
  def __init__(self, lit, **kwds):
    self.lit = lit
    IObject.__init__(self, **kwds)
  def __str__(self):
    return str(self.lit)
  def __repr__(self):
    return 'ILit(lit=%r)' % self.lit

class IReference(IObject):
  __metaclass__ = ABCMeta
IReference.register(IVar)
IReference.register(IVarAccess)
IReference.register(ILit)

class ICall(IObject):
  def __init__(self, name, exprs=[], **kwds):
    self.name = name
    self.exprs = exprs
    IObject.__init__(self, **kwds)
  @property
  def children(self):
    return self.exprs
  def __str__(self):
    string = ', '.join([repr(self.name)] + map(str, self.exprs))
    return '%s(%s)' % (self.__class__.__name__, string)
  def __repr__(self):
    return '%s(name=%r, exprs=%r)' % (type(self).__name__, self.name, self.exprs)

class IFCall(ICall): pass
class ICCall(ICall): pass

class IPartialCall(ICall):
  def __init__(self, name, missing, exprs, **kwds):
    ICall.__init__(self, name, exprs, **kwds)
    self.missing = int(missing)
  def __repr__(self):
    return '%s(name=%r, missing=%r, exprs=%r)' % (
        type(self).__name__, self.name, self.missing, self.exprs
      )

class IFPCall(IPartialCall): pass
class ICPCall(IPartialCall): pass

class IOr(IObject):
  def __init__(self, lhs, rhs, **kwds):
    self.lhs = lhs
    self.rhs = rhs
    IObject.__init__(self, **kwds)
  @property
  def children(self):
    return self.lhs, self.rhs
  def __str__(self):
    return '%s ? %s' % (self.lhs, self.rhs)
  def __repr__(self):
    return 'IOr(lhs=%r, rhs=%r)' % (self.lhs, self.rhs)

class IExpression(IObject):
  __metaclass__ = ABCMeta
IExpression.register(IVar)
IExpression.register(IVarAccess)
IExpression.register(ILit)
IExpression.register(ICall)
IExpression.register(IOr)

IExpr = IExpression

@dispatch.on('arg')
def modulename(arg):
  return modulename(arg.parent())

@modulename.when(IModule)
def modulename(arg):
  return arg.name

def iname(name):
  if not isinstance(name, IName):
    # Strip the module from a qualified name.
    name = '.'.join(name.split('.')[1:])
  assert name
  return name

def splitname(name):
  parts = name.split('.')
  return parts[0], '.'.join(parts[1:])

def joinname(*parts):
  return '.'.join(parts)


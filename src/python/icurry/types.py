from abc import ABCMeta
from collections import Iterator, OrderedDict, Mapping, Sequence
from ..utility import translateKwds
from ..utility.formatting import indent, wrapblock
from ..utility.proptree import proptree
from ..utility.visitation import dispatch
import logging
import re
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

class ISymbol(IObject):
  '''
  An IObject that appears in a symbol table.  Has ``fullname``, ``modulename``,
  ``name``, and ``parent`` attributes.  Derived types include modules, types,
  constructors, and functions.
  '''
  # The name is the unqualified name.  If the object belongs to a module or
  # package, then the prefix is stripped.
  @property
  def name(self):
    if not hasattr(self, '_name'):
      packagename = self.packagename
      if packagename is not None:
        assert self.fullname.startswith(packagename + '.')
        self._name = self.fullname[len(packagename)+1:]
      else:
        self._name = self.fullname
    return self._name

  @name.setter
  def name(self, name):
    self._name = name

  @property
  def modulename(self):
    '''
    Returns the fully-qualified name of the module containing a sybmol such as
    a function or constructor.

    Examples:
    ---------
        Prelude.: -> 'Prelude'
        Control.SetFunctions.Values -> 'Control.SetFunctions'
        Control.SetFunctions -> 'Control.SetFunctions'
        Control -> None
    '''
    if isinstance(self, IModule):
      return self.fullname
    else:
      try:
        parent = self.parent
      except AttributeError:
        return None
      else:
        return parent().modulename

  @property
  def packagename(self):
    '''
    Returns the qualifier of a name, which is the name of the containing module
    or package, if there is one.  For modules and packages, this returns the
    name of the contining package, if there is one, or None.  For other
    objects, such as functions and constructors, this is equivalent to
    ``modulename``.

    Examples:
    ---------
        Prelude.: -> 'Prelude'
        Control.SetFunctions.Values -> 'Control.SetFunctions'
        Control.SetFunctions -> 'Control'
        Control -> None
    '''
    if isinstance(self, (IPackage, IModule)):
      try:
        parent = self.parent
      except AttributeError:
        return None
      else:
        return parent().fullname
    else:
      return self.modulename

IArity = int
IVarIndex = int

class IInt(ISymbol):
  def __init__(self, value, **kwds):
    self.fullname = 'Prelude.Int'
    self.value = int(value)
    ISymbol.__init__(self, **kwds)
  def modulename(self):
    return 'Prelude'
  def __str__(self):
    return '(%r)' % self.value # parens to suggest boxing
  def __repr__(self):
    return 'IInt(value=%r)' % self.value

class IChar(ISymbol):
  def __init__(self, value, **kwds):
    self.fullname = 'Prelude.Char'
    self.value = str(value)
    assert len(self.value) in (1,2) # Unicode can have length 2 in utf-8
    ISymbol.__init__(self, **kwds)
  def modulename(self):
    return 'Prelude'
  def __str__(self):
    return '(%r)' % self.value # parens to suggest boxing
  def __repr__(self):
    return 'IChar(value=%r)' % self.value

class IFloat(ISymbol):
  def __init__(self, value, **kwds):
    self.fullname = 'Prelude.Float'
    self.value = float(value)
    ISymbol.__init__(self, **kwds)
  @property
  def modulename(self):
    return 'Prelude'
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

class IPackageOrModule(ISymbol):

  def setparent(self, parent):
    if parent is None:
      del self.__dict__['parent']
    else:
      assert isinstance(parent, IPackage)
      self.parent = weakref.ref(parent)
    return self

  @property
  def package(self):
    if hasattr(self, 'parent'):
      parent = self.parent()
      assert isinstance(parent, IPackage)
      return parent


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
    assert isinstance(submodule, (IPackage, IModule))
    assert submodule.fullname.startswith(self.fullname)
    shortname = submodule.fullname[len(self.fullname)+1:]
    key,_ = splitname(shortname)
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

  def __repr__(self):
    return 'IPackage(name=%r, submodules=%r)' % (self.fullname, self.submodules)


class IModule(IPackageOrModule):
  @translateKwds({'name': 'fullname'})
  def __init__(self, fullname, imports, types, functions, filename=None, **kwds):
    '''
    Parameters:
    -----------
      fullname    The fully-qualified module name.
      imports     A list of imported module names.
      types       A mapping or sequence of pairs: str -> [IConstructor].
      functions   A sequence of IFunctions, or a mapping or sequence of pairs
                  from string to IFunction.
    '''
    self.fullname = str(fullname)
    self.imports = tuple(set(str(x) for x in imports))
    self.types = symboltable(self, types)
    self.functions = symboltable(self, functions)
    self.filename = str(filename) if filename is not None else None
    ISymbol.__init__(self, **kwds)

  def __str__(self):
    return '\n'.join(
        [
            'Module:'
          , '-------'
          , '  name: %s' % self.name
          , '  fullname: %s' % self.fullname
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
        self.fullname, self.filename, self.imports, self.types.values(), self.functions.values()
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
        raise TypeError('cannot import %r from module %r' % (name, extern.fullname))

IProg = IModule

class IConstructor(ISymbol):
  def __init__(self, name, arity, **kwds):
    assert arity >= 0
    self.fullname = name
    self.arity = IArity(arity)
    ISymbol.__init__(self, **kwds)

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
    return 'IConstructor(name=%r, arity=%r)' % (self.fullname, self.arity)

class IDataType(ISymbol):
  def __init__(self, name, constructors, **kwds):
    self.fullname = name
    self.constructors = [ctor.setparent(self, i) for i,ctor in enumerate(constructors)]
    ISymbol.__init__(self, **kwds)

  def setparent(self, parent):
    assert isinstance(parent, IModule)
    self.parent = weakref.ref(parent)
    return self

  def __str__(self):
    return 'data %s = %s' % (self.name, ' | '.join(map(str, self.constructors)))

  def __repr__(self):
    return 'IDataType(name=%r, constructors=%r)' % (self.fullname, self.constructors)
IType = IDataType

class IFunction(ISymbol):
  def __init__(self, name, arity, vis=None, needed=None, body=[], **kwds):
    assert arity >= 0
    self.fullname = name
    self.arity = IArity(arity)
    self.vis = PUBLIC if vis is None else vis
    # None means no info; [] means nothing needed.
    self.needed = None if needed is None else map(int, needed)
    self.body = body
    ISymbol.__init__(self, **kwds)

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
    return 'IFunction(name=%r, arity=%r, vis=%r, needed=%r, body=%r)' % (
        self.fullname, self.arity, self.vis, self.needed, self.body
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
  @translateKwds({'name': 'symbolname'})
  def __init__(self, symbolname, **kwds):
    self.symbolname = str(symbolname)
    IObject.__init__(self, **kwds)
  def __str__(self):
    return 'extern(%s)' % self.symbolname
  def __repr__(self):
    return 'IExternal(symbolname=%r)' % self.symbolname

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
  def var(self):
    return IVar(self.vid)
  @property
  def children(self):
    return self.branches
  def __str__(self):
    return 'case %s of\n%s' % (
        self.var
      , indent(self.branches)
      )
  def __repr__(self):
    return '%s(vid=%r, branches=%r)' % (
        type(self).__name__, self.vid, self.branches
      )

class ICaseCons(ICase): pass
class ICaseLit(ICase): pass

class IConsBranch(IObject):
  @translateKwds({'name': 'typename'})
  def __init__(self, typename, arity, block, **kwds):
    self.typename = typename
    self.arity = arity
    self.block = block
    IObject.__init__(self, **kwds)
  @property
  def children(self):
    return self.block,
  def __str__(self):
    return '%s %s->%s' % (self.typename, ''.join('_ ' * self.arity), wrapblock(self.block))
  def __repr__(self):
    return 'IConsBranch(typename=%r, arity=%r, block=%r)' % (
        self.typename, self.arity, self.block
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
  @translateKwds({'name': 'symbolname'})
  def __init__(self, symbolname, exprs=[], **kwds):
    self.symbolname = symbolname
    self.exprs = exprs
    IObject.__init__(self, **kwds)
  @property
  def children(self):
    return self.exprs
  def __str__(self):
    string = ', '.join([repr(self.symbolname)] + map(str, self.exprs))
    return '%s(%s)' % (self.__class__.__name__, string)
  def __repr__(self):
    return '%s(symbolname=%r, exprs=%r)' % (
       type(self).__name__, self.symbolname, self.exprs
     )

class IFCall(ICall): pass
class ICCall(ICall): pass

class IPartialCall(ICall):
  @translateKwds({'name': 'symbolname'})
  def __init__(self, symbolname, missing, exprs, **kwds):
    ICall.__init__(self, symbolname, exprs, **kwds)
    self.missing = int(missing)
  def __repr__(self):
    return '%s(symbolname=%r, missing=%r, exprs=%r)' % (
        type(self).__name__, self.symbolname, self.missing, self.exprs
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

def splitname(name):
  parts = name.split('.')
  return parts[0], '.'.join(parts[1:])

def joinname(*parts):
  return '.'.join(parts)


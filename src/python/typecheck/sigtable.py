'''
The signature table: the type schemes of Curry symbols, read from the
FlatCurry interfaces that the front end writes.

The front end writes the interface ``M.fint`` of every module ``M`` it
compiles.  The interface holds the type of every function and constructor,
after the dictionary translation of the type classes, and the translation to
ICurry drops it.  This module reads the interface on demand.  It never parses
a whole file.  :class:`Interface` indexes the text once, with one regular
expression that skips quoted names, and records the offset of every ``Func``,
``Type``, ``TypeSyn``, ``TypeNew``, ``Cons`` and ``NewCons`` entry.  An entry
is decoded with the FlatCurry reader the first time a symbol asks for it.

A :class:`Scheme` is the type of one symbol.  The class context comes from
the leading dictionary parameters of the FlatCurry type: a constraint ``C a``
is a parameter of type ``() -> _Dict#C a``.  The scheme of a constructor
comes from its ``Type`` entry.  :func:`show_scheme` prints a scheme in Curry
syntax, for example ``Num a => a -> a -> a``.

The instances come from the names ``_inst#Class#Type`` of the loaded
modules; the context of an instance comes from its type.  The naming
convention is the one of curry-frontend 2.0.0, the front end of PAKCS 3.4.1.
The table checks for ``_inst#Prelude.Num#Prelude.Int`` when it reads the
interface of the Prelude.

One :class:`SignatureTable` belongs to one interpreter, as
``interp.sigtable``.  ``Interpreter.reset`` clears it.  A symbol without a
scheme is an error only when the caller asks for one with ``required=True``;
an untyped use of a symbol never reads the table.
'''

from .. import config, exceptions
from ..common import T_CTOR
from ..toolchain.flat2icurry import flatcurry as fc
from ..toolchain.flat2icurry.terms import constructor as _term
from ..utility import readcurry as rc
import logging, os, re, weakref

logger = logging.getLogger(__name__)

__all__ = [
    'Instance', 'Interface', 'InterfaceError', 'Predicate', 'Scheme'
  , 'SignatureTable', 'find_interface', 'interface_candidates', 'module_root'
  , 'show_predicate', 'show_scheme', 'show_type', 'typevar_name'
  ]

PRELUDE = 'Prelude'
DICT_PREFIX = '_Dict#'
INST_PREFIX = '_inst#'
# The instance the table looks for when it reads the interface of the
# Prelude.  The name follows curry-frontend 2.0.0; version 3.0.0 renames the
# instance functions.
NUM_INT_INSTANCE = '_inst#Prelude.Num#Prelude.Int'
UNIT = fc.TCons(fc.prelude('()'), [])

class InterfaceError(exceptions.CurryTypeError):
  '''
  An interface is missing or unreadable, a needed entry is absent, or a name
  does not follow the convention of the pinned front end.
  '''

# Types without an interface entry.  Sprite's Prelude declares the boxed
# literals Int, Char and Float as constructors with one unboxed argument.
# Their schemes are the nullary types.  The other symbols of Sprite's own
# Prelude, the arrow, IO, the lifted case and let functions, and the builders
# of Python strings and iterators, have no scheme.
BUILTIN_SCHEMES = {
    (PRELUDE, 'Int')   : fc.TCons(fc.prelude('Int'), [])
  , (PRELUDE, 'Char')  : fc.TCons(fc.prelude('Char'), [])
  , (PRELUDE, 'Float') : fc.TCons(fc.prelude('Float'), [])
  }

# The schemes
# ===========
class Predicate(_term('Predicate', 'classname typeexpr')):
  '''
  A class constraint ``C t``.  ``classname`` is the qualified name of the
  class, e.g., ``Prelude.Num``; ``typeexpr`` is the constrained type.
  '''
  __slots__ = ()

  def __str__(self):
    return show_predicate(self)

class Scheme:
  '''
  The type scheme of one symbol.

  Attributes:
    modulename:
        The module of the symbol.
    name:
        The name of the symbol in its module.
    typevars:
        The quantified type variables as pairs ``(index, kind)``, the top
        quantifier first, then the own quantifier of a class method.
    context:
        The class constraints, a tuple of :class:`Predicate`, recovered from
        the leading dictionary parameters in their order.
    typeexpr:
        The type without the dictionary parameters and the quantifiers.
    arity:
        The FlatCurry arity.  The leading dictionary parameters count.
    ndicts:
        The number of dictionary parameters, in the order the symbol takes
        them.  A class method with its own constraints, such as ``round``,
        takes the dictionaries of those constraints after its FlatCurry
        parameters.
    flat_typeexpr:
        The type as the interface writes it, dictionaries and quantifiers
        included.  None for a built-in scheme.
    is_constructor:
        Whether the symbol is a data constructor.
  '''
  __slots__ = (
      'modulename', 'name', 'typevars', 'context', 'typeexpr', 'arity'
    , 'ndicts', 'flat_typeexpr', 'is_constructor'
    )

  def __init__(
      self, modulename, name, typevars, context, typeexpr, arity, ndicts
    , flat_typeexpr=None, is_constructor=False
    ):
    self.modulename = modulename
    self.name = name
    self.typevars = tuple(typevars)
    self.context = tuple(context)
    self.typeexpr = typeexpr
    self.arity = arity
    self.ndicts = ndicts
    self.flat_typeexpr = flat_typeexpr
    self.is_constructor = is_constructor

  @property
  def fullname(self):
    return '%s.%s' % (self.modulename, self.name)

  @property
  def source_arity(self):
    '''
    The number of value parameters among the FlatCurry parameters: the arity
    less the dictionaries, at least zero.
    '''
    return max(self.arity - self.ndicts, 0)

  def __str__(self):
    return show_scheme(self)

  def __repr__(self):
    return '<Scheme %s :: %s>' % (self.fullname, self)

class Instance:
  '''
  A class instance, from the function ``_inst#Class#Type`` of the module that
  declares it.

  Attributes:
    classname:
        The qualified class name, e.g., ``Prelude.Show``.
    typename:
        The type constructor as the name spells it: qualified, e.g.,
        ``Prelude.Maybe``, or one of the special constructors ``[]``, ``()``,
        ``(,)`` and so on, and ``(->)``.
    modulename:
        The module that declares the instance.
    name:
        The name of the instance function in that module.
    scheme:
        The scheme of the instance function.  Its context is the instance
        context; its type is ``() -> _Dict#Class head``.
  '''
  __slots__ = ('classname', 'typename', 'modulename', 'name', 'scheme')

  def __init__(self, classname, typename, modulename, name, scheme):
    self.classname = classname
    self.typename = typename
    self.modulename = modulename
    self.name = name
    self.scheme = scheme

  @property
  def fullname(self):
    return '%s.%s' % (self.modulename, self.name)

  @property
  def context(self):
    return self.scheme.context

  @property
  def head(self):
    '''The instance head, e.g., ``TCons ("Prelude","Maybe") [TVar 0]``.'''
    result = self.scheme.typeexpr
    if isinstance(result, fc.FuncType):
      result = result.range
    assert isinstance(result, fc.TCons) and len(result.args) == 1
    return result.args[0]

  def __repr__(self):
    return '<Instance %s %s from %s>' % (
        self.classname, self.typename, self.fullname
      )

def dict_predicate(typeexpr):
  '''
  The predicate of a dictionary parameter: ``() -> _Dict#C t`` gives
  ``Predicate('M.C', t)``.  Returns None for another type.
  '''
  if isinstance(typeexpr, fc.FuncType) and typeexpr.domain == UNIT:
    rng = typeexpr.range
    if isinstance(rng, fc.TCons) and len(rng.args) == 1:
      modulename, name = rng.name
      if name.startswith(DICT_PREFIX):
        classname = '%s.%s' % (modulename, name[len(DICT_PREFIX):])
        return Predicate(classname, rng.args[0])
  return None

def scheme_of_function(func):
  '''
  The scheme of a FlatCurry ``Func`` entry.  The dictionary parameters are
  collected past every quantifier.  A class method quantifies its own
  variables after the dictionary of its class, and a method with its own
  constraints, such as ``round :: (RealFrac a, Integral b) => a -> b``, has
  more dictionaries after that quantifier.
  '''
  modulename, name = func.name
  typevars = []
  context = []
  nleading = None
  typeexpr = func.typeexpr
  while True:
    if isinstance(typeexpr, fc.ForallType):
      # A quantifier after the dictionaries ends the FlatCurry parameters.
      if context and nleading is None:
        nleading = len(context)
      typevars.extend(typeexpr.typevars)
      typeexpr = typeexpr.typeexpr
      continue
    if isinstance(typeexpr, fc.FuncType):
      pred = dict_predicate(typeexpr.domain)
      if pred is not None:
        context.append(pred)
        typeexpr = typeexpr.range
        continue
    break
  if nleading is None:
    nleading = len(context)
  if nleading > func.arity:
    logger.warning(
        '%s.%s has %d dictionary parameters but arity %d'
      , modulename, name, nleading, func.arity
      )
  return Scheme(
      modulename, name, typevars, context, typeexpr, func.arity, len(context)
    , flat_typeexpr=func.typeexpr
    )

def scheme_of_constructor(typedecl, consdecl):
  '''
  The scheme of a constructor from its ``Type`` or ``TypeNew`` entry: the
  argument types lead to the declared type applied to its variables.
  '''
  modulename, name = consdecl.name
  typevars = list(typedecl.typevars)
  result = fc.TCons(typedecl.name, [fc.TVar(i) for i, _ in typevars])
  if isinstance(consdecl, fc.NewCons):
    argtypes = [consdecl.typeexpr]
  else:
    argtypes = list(consdecl.argtypes)
  typeexpr = result
  for argtype in reversed(argtypes):
    typeexpr = fc.FuncType(argtype, typeexpr)
  flat = fc.ForallType(typevars, typeexpr) if typevars else typeexpr
  return Scheme(
      modulename, name, typevars, (), typeexpr, len(argtypes), 0
    , flat_typeexpr=flat, is_constructor=True
    )

def builtin_scheme(modulename, name):
  '''The scheme of a symbol of Sprite's own Prelude, or None.'''
  typeexpr = BUILTIN_SCHEMES.get((modulename, name))
  if typeexpr is None:
    return None
  return Scheme(
      modulename, name, (), (), typeexpr, 0, 0, is_constructor=True
    )

# The printer
# ===========
def typevar_name(i):
  '''The name of the i-th type variable: a to z, then a1 to z1, and so on.'''
  q, r = divmod(i, 26)
  return chr(ord('a') + r) + (str(q) if q else '')

class _Names:
  '''Names the type variables in the order of their first use.'''
  def __init__(self, names=None):
    self.names = {} if names is None else dict(names)

  def __call__(self, index):
    name = self.names.get(index)
    if name is None:
      used = set(self.names.values())
      i = 0
      while typevar_name(i) in used:
        i += 1
      name = self.names[index] = typevar_name(i)
    return name

def _collect_typevars(typeexpr, names):
  '''Names the variables of a type in the order of their first occurrence.'''
  stack = [typeexpr]
  while stack:
    te = stack.pop()
    if isinstance(te, fc.TVar):
      names(te.index)
    elif isinstance(te, fc.FuncType):
      stack.append(te.range)
      stack.append(te.domain)
    elif isinstance(te, fc.TCons):
      stack.extend(reversed(te.args))
    elif isinstance(te, fc.ForallType):
      stack.append(te.typeexpr)

def _paren(text, yes):
  return '(%s)' % text if yes else text

def _is_tuple_name(name):
  return len(name) > 2 and name[0] == '(' and name[-1] == ')' \
      and set(name[1:-1]) == {','}

def _qualify(qname, module):
  '''Writes a name unqualified when it belongs to the Prelude or to ``module``.'''
  modulename, name = qname
  if modulename == PRELUDE or modulename == module:
    return name
  return '%s.%s' % (modulename, name)

# Precedence levels of the printer: 0 allows an arrow, 1 is the domain of an
# arrow or the head of an application, 2 is the argument of an application.
def _show(te, names, prec, module):
  if isinstance(te, fc.TVar):
    return names(te.index)
  if isinstance(te, fc.FuncType):
    text = '%s -> %s' % (
        _show(te.domain, names, 1, module), _show(te.range, names, 0, module)
      )
    return _paren(text, prec > 0)
  if isinstance(te, fc.ForallType):
    text = 'forall %s. %s' % (
        ' '.join(names(i) for i, _ in te.typevars)
      , _show(te.typeexpr, names, 0, module)
      )
    return _paren(text, prec > 0)
  if isinstance(te, fc.TCons):
    modulename, name = te.name
    args = te.args
    if modulename == PRELUDE:
      if name == '[]' and len(args) == 1:
        return '[%s]' % _show(args[0], names, 0, module)
      if name == '()' and not args:
        return '()'
      if _is_tuple_name(name) and len(args) == len(name) - 1:
        return '(%s)' % ', '.join(_show(a, names, 0, module) for a in args)
      if name == '(->)' and len(args) == 2:
        return _show(fc.FuncType(*args), names, prec, module)
      if name == 'Apply' and len(args) == 2:
        text = '%s %s' % (
            _show(args[0], names, 1, module), _show(args[1], names, 2, module)
          )
        return _paren(text, prec > 1)
    head = _qualify(te.name, module)
    if not args:
      return head
    text = ' '.join([head] + [_show(a, names, 2, module) for a in args])
    return _paren(text, prec > 1)
  raise TypeError('not a type expression: %r' % (te,))

def show_type(typeexpr, names=None, module=None):
  '''
  Prints a type in Curry syntax.  Variables are named a, b, c, ... in the
  order of their first occurrence; ``names`` may be a mapping from variable
  index to name.  Names of the Prelude and of ``module`` are unqualified.
  '''
  return _show(typeexpr, _Names(names), 0, module)

def show_predicate(pred, names=None, module=None):
  '''Prints a class constraint, e.g., ``Show (Maybe a)``.'''
  names = _Names(names)
  classname = _qualify(tuple(pred.classname.rsplit('.', 1)), module)
  return '%s %s' % (classname, _show(pred.typeexpr, names, 2, module))

def show_scheme(scheme, module=None, qualify=None):
  '''
  Prints a scheme in Curry syntax with the context folded back, e.g.,
  ``Num a => a -> a -> a``.  The variables are named in the order of their
  first occurrence in the type; a variable of the context alone comes last.
  Names of the Prelude and of the scheme's own module are unqualified;
  ``module`` names another module whose names stay unqualified, and
  ``qualify=True`` qualifies every name outside the Prelude.
  '''
  if qualify:
    module = None
  elif module is None:
    module = scheme.modulename
  names = _Names()
  _collect_typevars(scheme.typeexpr, names)
  for pred in scheme.context:
    _collect_typevars(pred.typeexpr, names)
  body = _show(scheme.typeexpr, names, 0, module)
  if not scheme.context:
    return body
  preds = [show_predicate(pred, names.names, module) for pred in scheme.context]
  if len(preds) == 1:
    return '%s => %s' % (preds[0], body)
  return '(%s) => %s' % (', '.join(preds), body)

# The index of one interface
# ==========================
# One pass finds the entries.  A quoted name is matched first, so that a
# name such as "(,)" or an operator never starts an entry or ends one.
_ENTRY = re.compile(
    rb'"(?:[^"\\]|\\.)*"'
    rb'|\b(?P<kind>Func|TypeSyn|TypeNew|Type|NewCons|Cons)'
    rb' \("(?P<module>(?:[^"\\]|\\.)*)","(?P<name>(?:[^"\\]|\\.)*)"\)'
  )
_HEADER = re.compile(rb'Prog "(?P<name>(?:[^"\\]|\\.)*)" \[(?P<imports>[^\]]*)\]')
_QUOTED = re.compile(rb'"(?:[^"\\]|\\.)*"')
_DELIM = re.compile(rb'["()\[\],]')
_TYPE_KINDS = (b'Type', b'TypeSyn', b'TypeNew')

def _unquote(raw):
  '''The text of a quoted name without its quotes.'''
  if b'\\' not in raw:
    return raw.decode('utf-8')
  return str(rc.parse('"%s"' % raw.decode('utf-8')))

class Interface:
  '''
  One FlatCurry interface, indexed by the offsets of its entries.

  Attributes:
    path:
        The file.
    data:
        Its text, as bytes.
    name:
        The module name the interface declares.
    imports:
        The imported modules.
  '''
  # The interfaces read in this process, by file.  The key holds the size
  # and the modification time, so a rewritten file is read again.
  _loaded = {}

  def __init__(self, path, data=None):
    if data is None:
      with open(path, 'rb') as istream:
        data = istream.read()
    self.path = path
    self.data = data
    header = _HEADER.match(data)
    if header is None:
      raise InterfaceError('%s is not a FlatCurry interface' % path)
    self.name = _unquote(header.group('name'))
    self.imports = tuple(
        _unquote(m.group()[1:-1])
            for m in _QUOTED.finditer(header.group('imports'))
      )
    self._funcs = {}
    self._types = {}
    self._ctors = {}
    self._decoded = {}
    self._index()

  @classmethod
  def load(cls, path):
    '''Reads an interface.  Files are cached by name, size, and time.'''
    st = os.stat(path)
    key = (path, st.st_size, st.st_mtime_ns)
    iface = cls._loaded.get(key)
    if iface is None:
      iface = cls._loaded[key] = cls(path)
    return iface

  @classmethod
  def purge(cls):
    '''Forgets the cached interfaces whose files are gone.'''
    for key in list(cls._loaded):
      if not os.path.isfile(key[0]):
        del cls._loaded[key]

  def __repr__(self):
    return '<Interface %s at %s>' % (self.name, self.path)

  def _index(self):
    last_type = None
    for m in _ENTRY.finditer(self.data):
      kind = m.group('kind')
      if kind is None:
        continue
      name = _unquote(m.group('name'))
      if kind == b'Func':
        self._funcs[name] = m.start()
      elif kind in _TYPE_KINDS:
        self._types[name] = m.start()
        last_type = name
      else:
        self._ctors[name] = (last_type, m.start())

  def _end(self, start):
    '''The end of the entry at ``start``: the first unmatched bracket or comma.'''
    depth = 0
    pos = start
    while True:
      m = _DELIM.search(self.data, pos)
      if m is None:
        return len(self.data)
      c = m.group()
      if c == b'"':
        pos = _QUOTED.match(self.data, m.start()).end()
        continue
      if c in b'([':
        depth += 1
      elif c == b',':
        if depth == 0:
          return m.start()
      else:
        if depth == 0:
          return m.start()
        depth -= 1
      pos = m.end()

  def _decode(self, start):
    term = self._decoded.get(start)
    if term is None:
      text = self.data[start:self._end(start)].decode('utf-8')
      try:
        term = fc.decode(rc.parse(text))
      except (Exception, fc.Flat2ICurryError) as err:
        raise InterfaceError(
            'cannot decode the entry at offset %d of %s: %s'
                % (start, self.path, err)
          ) from err
      self._decoded[start] = term
    return term

  def function_names(self):
    return self._funcs.keys()

  def type_names(self):
    return self._types.keys()

  def constructor_names(self):
    return self._ctors.keys()

  def function(self, name):
    '''The ``Func`` entry of ``name``, or None.'''
    start = self._funcs.get(name)
    return None if start is None else self._decode(start)

  def type_decl(self, name):
    '''The ``Type``, ``TypeSyn`` or ``TypeNew`` entry of ``name``, or None.'''
    start = self._types.get(name)
    return None if start is None else self._decode(start)

  def constructor(self, name):
    '''
    The constructor ``name``: a pair of its type declaration and its ``Cons``
    or ``NewCons`` entry, or None.
    '''
    entry = self._ctors.get(name)
    if entry is None:
      return None
    typename, start = entry
    return self.type_decl(typename), self._decode(start)

  def scheme(self, name, is_constructor=False):
    '''The scheme of a function or constructor of this module, or None.'''
    if is_constructor:
      entry = self.constructor(name)
      return None if entry is None else scheme_of_constructor(*entry)
    func = self.function(name)
    return None if func is None else scheme_of_function(func)

  def instance_names(self):
    '''The names of the instance functions, ``_inst#Class#Type``.'''
    return [name for name in self._funcs if name.startswith(INST_PREFIX)]

# Finding the file
# ================
def module_root(dirname, modulename):
  '''
  The root of the module ``modulename`` whose source lies in ``dirname``: the
  directory without the package path.  The root of ``A.B`` at ``<root>/A/B.curry``
  is ``<root>``.
  '''
  parts = modulename.split('.')[:-1]
  if parts:
    tail = os.sep + os.path.join(*parts)
    if dirname.endswith(tail):
      return dirname[:-len(tail)] or os.sep
  return dirname

def interface_candidates(filename, modulename):
  '''
  The places where the interface of a module may lie, in the order of the
  search.  ``filename`` is the Curry source.  The copy beside the module's
  ICurry file is read, under the directory of the source and under the root
  of the module; the step that writes the ICurry file writes it (see
  ``cache.INTERFACE_SUFFIXES``).  The front end's own copy under
  ``.curry/<frontend_subdir>/`` is never read: after a hit of the ICurry
  cache it can belong to another version of the source.
  '''
  filename = os.path.abspath(filename)
  dirname, base = os.path.split(filename)
  stem = base[:-len('.curry')] if base.endswith('.curry') else base
  parts = modulename.split('.')[:-1]
  root = module_root(dirname, modulename)
  tail = stem + '.fint'
  candidates = [
      os.path.join(dirname, '.curry', config.intermediate_subdir(), tail)
    , os.path.join(root, '.curry', config.intermediate_subdir(), *parts, tail)
    ]
  return list(dict.fromkeys(candidates))

def find_interface(filename, modulename):
  '''The interface file of a module, or None.'''
  for candidate in interface_candidates(filename, modulename):
    if os.path.isfile(candidate):
      return candidate
  return None

# The table
# =========
class _ModuleEntry:
  '''What the table knows about one loaded module.'''
  __slots__ = ('interface', 'schemes', 'instances')

  def __init__(self, interface):
    self.interface = interface
    self.schemes = {}
    self.instances = None

def parse_instance_name(name, modulename):
  '''Splits ``_inst#Class#Type`` into the class and the type names.'''
  parts = name.split('#')
  if len(parts) != 3 or parts[0] != INST_PREFIX[:-1] or not all(parts[1:]):
    raise InterfaceError(
        'cannot read the instance name %r of module %s; the table expects '
        'the names of curry-frontend 2.0.0, _inst#Class#Type'
            % (name, modulename)
      )
  return parts[1], parts[2]

class SignatureTable:
  '''
  The type schemes of the symbols of one interpreter.

  The table finds the interface of a module from the module's source file
  (:func:`interface_candidates`), indexes it once, and decodes one entry
  per symbol on first use.  It memoizes per module object, so the modules
  of ``compile(mode='expr')`` are served while they live.  :meth:`clear`
  forgets everything; ``Interpreter.reset`` calls it.
  '''
  def __init__(self, interp):
    self._interp = weakref.ref(interp)
    self._modules = weakref.WeakKeyDictionary()
    self._instances = {}

  @property
  def interp(self):
    return self._interp()

  def clear(self):
    '''Forgets every interface, scheme and instance.'''
    self._modules.clear()
    self._instances.clear()
    Interface.purge()

  def modules(self):
    '''The names of the modules whose interface the table has found.'''
    return [
        module.__name__ for module, entry in self._modules.items()
                        if entry.interface is not None
      ]

  # Interfaces.
  def _module(self, module):
    '''
    The module object of ``module``: a module object, or the name of a
    loaded module or of a module of the system library, which is imported.
    '''
    if isinstance(module, str):
      return self.interp.module(module)
    return module

  def _entry(self, module):
    module = self._module(module)
    entry = self._modules.get(module)
    if entry is None:
      entry = self._modules[module] = _ModuleEntry(self._find(module))
    return entry

  def _find(self, module):
    '''Finds and indexes the interface of a module object, or None.'''
    from ..objects.handle import getHandle
    handle = getHandle(module)
    if handle.is_package:
      return None
    filename = handle.icurry.filename
    if filename is None:
      logger.debug('module %s has no source file', module.__name__)
      return None
    path = find_interface(filename, handle.fullname)
    if path is None:
      logger.debug(
          'no FlatCurry interface for module %s; tried %s'
        , module.__name__, ', '.join(interface_candidates(filename, handle.fullname))
        )
      return None
    iface = Interface.load(path)
    logger.debug('module %s has its interface at %s', module.__name__, path)
    if handle.fullname == PRELUDE:
      self.check_frontend(iface)
    return iface

  @staticmethod
  def check_frontend(iface):
    '''
    Checks that an interface of the Prelude names its instances as
    curry-frontend 2.0.0 does.  Raises :class:`InterfaceError` otherwise.
    '''
    if NUM_INT_INSTANCE not in iface.function_names():
      raise InterfaceError(
          'the FlatCurry interface %s has no entry %s; the signature table '
          'expects the naming convention of curry-frontend 2.0.0, the front '
          'end of PAKCS 3.4.1' % (iface.path, NUM_INT_INSTANCE)
        )

  def interface(self, module):
    '''
    The :class:`Interface` of a module, given as a module object or as the
    name of a loaded module, or None when no interface file exists.
    '''
    return self._entry(module).interface

  def interface_filename(self, module):
    '''The interface file of a module, or None.'''
    iface = self.interface(module)
    return None if iface is None else iface.path

  # Schemes.
  def lookup(self, symbol, required=False):
    '''
    The :class:`Scheme` of a symbol, or None when the symbol has none.

    Args:
      symbol:
          A ``CurryNodeInfo`` or the fully-qualified name of a symbol of a
          loaded module.
      required:
          Whether a missing scheme is an error.  The typed path asks for a
          scheme that way; an untyped use never asks.

    Raises:
      InterfaceError:
          ``required`` is set and the symbol has no scheme.
    '''
    if isinstance(symbol, str):
      symbol = self.interp.symbol(symbol)
    icur = getattr(symbol, 'icurry', None)
    if icur is None:
      return self._missing(symbol, required, 'the symbol has no ICurry')
    modulename, name = icur.modulename, icur.name
    scheme = builtin_scheme(modulename, name)
    if scheme is not None:
      return scheme
    module = getattr(symbol, '_module', None)
    module = None if module is None else module()
    if module is None:
      return self._missing(symbol, required, 'the module is gone')
    entry = self._entry(module)
    is_constructor = symbol.info.tag >= T_CTOR
    key = name, is_constructor
    if key not in entry.schemes:
      iface = entry.interface
      scheme = None if iface is None else iface.scheme(name, is_constructor)
      entry.schemes[key] = scheme
    scheme = entry.schemes[key]
    if scheme is None:
      if entry.interface is None:
        return self._missing(symbol, required, None)
      return self._missing(
          symbol, required
        , 'the FlatCurry interface %s has no entry %r' % (entry.interface.path, name)
        )
    return scheme

  @staticmethod
  def _missing(symbol, required, reason):
    if not required:
      return None
    icur = getattr(symbol, 'icurry', None)
    fullname = symbol if icur is None else icur.fullname
    modulename = fullname.rpartition('.')[0] if icur is None else icur.modulename
    if reason is None:
      raise InterfaceError(
          'no type for %s: no FlatCurry interface found; recompile %s or use '
          'raw_expr' % (fullname, modulename)
        )
    raise InterfaceError('no type for %s: %s; use raw_expr' % (fullname, reason))

  def type_decl(self, typename):
    '''
    The ``Type``, ``TypeSyn`` or ``TypeNew`` entry of a type, given by its
    fully-qualified name, e.g., ``Prelude.IO``, or None.
    '''
    modulename, _, name = typename.rpartition('.')
    iface = self.interface(modulename)
    return None if iface is None else iface.type_decl(name)

  # Instances.
  def instances(self):
    '''
    The instance map over the loaded modules: a dict from the pair of the
    qualified class name and the type constructor name to the
    :class:`Instance`.  Every loaded module is scanned for its
    ``_inst#Class#Type`` functions.  Two modules that declare the same
    instance are an error.
    '''
    for modulename, module in list(self.interp.modules.items()):
      entry = self._entry(module)
      if entry.instances is not None:
        continue
      found = []
      iface = entry.interface
      if iface is not None:
        for name in iface.instance_names():
          classname, typename = parse_instance_name(name, modulename)
          scheme = scheme_of_function(iface.function(name))
          inst = Instance(classname, typename, modulename, name, scheme)
          prev = self._instances.get((classname, typename))
          if prev is not None and prev.modulename != modulename:
            raise InterfaceError(
                'instance %s %s is declared in module %s and in module %s'
                    % (classname, typename, prev.modulename, modulename)
              )
          self._instances[classname, typename] = inst
          found.append(inst)
      entry.instances = found
    return self._instances

  def instance(self, classname, typename):
    '''
    The :class:`Instance` of a class at a type constructor, or None.  The
    class is qualified, e.g., ``Prelude.Show``; the type constructor is
    qualified or special, e.g., ``Prelude.Maybe`` or ``[]``.
    '''
    return self.instances().get((classname, typename))

  def instances_of(self, classname):
    '''The instances of one class, by type constructor name.'''
    return {
        typename: inst for (cls, typename), inst in self.instances().items()
                       if cls == classname
      }

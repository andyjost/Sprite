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

The instances come from the operation names of the loaded modules; their
contexts come from their types. Both the head-only names of front end 2.0.0
and the recursively delimited type names of front end 3.1.0 are read.

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
from ..utility.trampoline import trampoline
import logging, os, re, weakref, threading
from ..utility.locking import synchronized

logger = logging.getLogger(__name__)

__all__ = [
    'Instance', 'Interface', 'InterfaceError', 'Predicate', 'Scheme'
  , 'SignatureTable', 'find_interface', 'interface_candidates', 'module_root'
  , 'show_predicate', 'show_scheme', 'show_type', 'typevar_name'
  ]

PRELUDE = 'Prelude'
DICT_PREFIX = '_Dict#'
INST_PREFIX = '_inst#'
NUM_INT_INSTANCE = '_inst#Prelude.Num#Prelude.Int'
UNIT = fc.TCons(fc.prelude('()'), [])

class InterfaceError(exceptions.CurryTypeError):
  '''
  An interface is missing or unreadable, a needed entry is absent, or a name
  does not follow either supported front end's convention.
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
    if isinstance(rng, fc.TCons):
      modulename, name = rng.name
      if name.startswith(DICT_PREFIX):
        classname = '%s.%s' % (modulename, name[len(DICT_PREFIX):])
        if len(rng.args) != 1:
          unsupported_class(classname, len(rng.args))
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
  return trampoline(_show_walk(te, names, prec, module))

def _show_walk(te, names, prec, module):
  if isinstance(te, fc.TVar):
    return names(te.index)
  if isinstance(te, fc.FuncType):
    text = '%s -> %s' % (
        (yield _show_walk(te.domain, names, 1, module)),
        (yield _show_walk(te.range, names, 0, module))
      )
    return _paren(text, prec > 0)
  if isinstance(te, fc.ForallType):
    text = 'forall %s. %s' % (
        ' '.join(names(i) for i, _ in te.typevars)
      , (yield _show_walk(te.typeexpr, names, 0, module))
      )
    return _paren(text, prec > 0)
  if isinstance(te, fc.TCons):
    modulename, name = te.name
    args = te.args
    if modulename == PRELUDE:
      if name == '[]' and len(args) == 1:
        return '[%s]' % (yield _show_walk(args[0], names, 0, module))
      if name == '()' and not args:
        return '()'
      if _is_tuple_name(name) and len(args) == len(name) - 1:
        parts = []
        for arg in args:
          parts.append((yield _show_walk(arg, names, 0, module)))
        return '(%s)' % ', '.join(parts)
      if name == '(->)' and len(args) == 2:
        return (yield _show_walk(fc.FuncType(*args), names, prec, module))
      if name == 'Apply' and len(args) == 2:
        text = '%s %s' % (
            (yield _show_walk(args[0], names, 1, module)),
            (yield _show_walk(args[1], names, 2, module))
          )
        return _paren(text, prec > 1)
    head = _qualify(te.name, module)
    if not args:
      return head
    parts = [head]
    for arg in args:
      parts.append((yield _show_walk(arg, names, 2, module)))
    text = ' '.join(parts)
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
  _cache_lock = threading.RLock()

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
    self._decode_lock = threading.RLock()
    self._index()

  @classmethod
  @synchronized(_cache_lock)
  def load(cls, path):
    '''Reads an interface.  Files are cached by name, size, and time.'''
    st = os.stat(path)
    key = (path, st.st_size, st.st_mtime_ns)
    iface = cls._loaded.get(key)
    if iface is None:
      iface = cls._loaded[key] = cls(path)
    return iface

  @classmethod
  @synchronized(_cache_lock)
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
    with self._decode_lock:
      return self._decode_locked(start)

  def _decode_locked(self, start):
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

def unsupported_class(classname, arity):
  raise InterfaceError(
      '%s class %s is not supported by the typed API'
          % ('nullary' if arity == 0 else 'multi-parameter', classname))

def _type_name(te):
  if isinstance(te, fc.TVar):
    return str(te.index)
  if isinstance(te, fc.FuncType):
    return '(->)'
  if isinstance(te, fc.TCons) and te.name == fc.prelude('Apply'):
    return _type_name(te.args[0])
  module, name = te.name
  return name if not module or module == PRELUDE and (
      name in ('[]', '()', '(->)') or _is_tuple_name(name)
    ) else '%s.%s' % te.name

def _named_type(name, args=()):
  if name.isdecimal():
    if args:
      # A higher-kinded variable applied to types.
      return fc.TCons(fc.prelude('Apply'), [fc.TVar(int(name))] + list(args))
    return fc.TVar(int(name))
  if name == '(->)' and len(args) == 2:
    return fc.FuncType(*args)
  module, sep, short = name.rpartition('.')
  if sep:
    qname = module, short
  elif name in ('[]', '()', '(->)') or _is_tuple_name(name):
    qname = fc.prelude(name)
  else:
    qname = '', name
  return fc.TCons(qname, list(args))

def _encoded_type(te):
  if isinstance(te, fc.ForallType):
    return _encoded_type(te.typeexpr)
  if isinstance(te, fc.FuncType):
    args = (te.domain, te.range)
  else:
    args = te.args if isinstance(te, fc.TCons) else ()
  if isinstance(te, fc.TCons) and te.name == fc.prelude('Apply'):
    head, *args = te.args
    atom = _encoded_type(head)[1:-1]
  else:
    atom = _type_name(te)
  return '#' + atom + ''.join(_encoded_type(arg) for arg in args) + '#'

def instance_name(classname, *types, version=None):
  '''Build an instance identifier in the configured front end's spelling.'''
  version = config.frontend_version() if version is None else version
  if version < '3.0.0':
    if len(types) != 1:
      unsupported_class(classname, len(types))
    return INST_PREFIX + classname + '#' + _type_name(types[0])
  return INST_PREFIX + classname + ''.join(map(_encoded_type, types))

def implementation_name(method, classname, *types, version=None):
  return '_impl#' + method + '#' + instance_name(
      classname, *types, version=version)[len(INST_PREFIX):]

def parse_instance_types(name, modulename):
  '''Read old head-only names or Dictionary.typeId's recursive #type# form.'''
  try:
    prefix, suffix = name.split('#', 1)
    classname, sep, tail = suffix.partition('#')
    if prefix != INST_PREFIX[:-1] or not classname:
      raise ValueError()
    if not sep:
      if re.fullmatch(r'[^\s()\[\]]+', classname) is None:
        raise ValueError()
      return classname, ()
    if not tail:
      raise ValueError()
    if '#' not in tail:
      return classname, (_named_type(tail),)
    text = '#' + tail
    def read(pos):
      if text[pos] != '#':
        raise ValueError()
      end = text.index('#', pos + 1)
      atom = text[pos + 1:end]
      if not atom:
        raise ValueError()
      args = []
      while end + 1 < len(text) and text[end + 1] != '#':
        arg, end = read(end)
        args.append(arg)
      if end >= len(text) or text[end] != '#':
        raise ValueError()
      return _named_type(atom, args), end + 1
    types, pos = [], 0
    while pos < len(text):
      ty, pos = read(pos)
      types.append(ty)
    return classname, tuple(types)
  except (ValueError, IndexError):
    raise InterfaceError(
        'cannot read the instance name %r of module %s' % (name, modulename)
      ) from None

def parse_instance_name(name, modulename):
  '''The unary class and head atom, rejecting non-unary classes.'''
  classname, types = parse_instance_types(name, modulename)
  if len(types) != 1:
    unsupported_class(classname, len(types))
  return classname, _type_name(types[0])

class SignatureTable:
  '''
  The type schemes of the symbols of one interpreter.

  The table finds the interface of a module from the module's source file
  (:func:`interface_candidates`), indexes it once, and decodes one entry
  per symbol on first use.  It memoizes per module object, so the modules
  of the internal expression compiler are served while they live.  :meth:`clear`
  forgets everything; ``Interpreter.reset`` calls it.
  '''
  def __init__(self, interp):
    self._interp = weakref.ref(interp)
    self._modules = {}
    self._instances = {}
    self._unsupported_classes = {}
    self._lock = threading.RLock()

  @property
  def interp(self):
    return self._interp()

  def clear(self):
    '''Forgets every interface, scheme and instance.'''
    with self._lock:
      self._modules.clear()
      self._instances.clear()
      self._unsupported_classes.clear()
    Interface.purge()

  def modules(self):
    '''The names of the modules whose interface the table has found.'''
    with self._lock:
      modules = [(ref(), entry) for ref, entry in self._modules.values()]
    return [
        module.__name__ for module, entry in modules
                        if module is not None and entry.interface is not None
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
    key = id(module)
    with self._lock:
      found = self._modules.get(key)
      entry = None if found is None or found[0]() is not module else found[1]
    if entry is None:
      candidate = _ModuleEntry(self._find(module))
      def forget(ref):
        with self._lock:
          found = self._modules.get(key)
          if found is not None and found[0] is ref:
            del self._modules[key]
      ref = weakref.ref(module, forget)
      with self._lock:
        found = self._modules.setdefault(key, (ref, candidate))
        entry = found[1]
    return entry

  def _find(self, module):
    '''Finds and indexes the interface of a module object, or None.'''
    from ..objects.handle import getHandle
    handle = getHandle(module)
    if handle.is_package:
      return None
    embedded = getattr(module, '.interface_file', None)
    if embedded is not None:
      return Interface.load(embedded)
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
    either supported front end does. Raises :class:`InterfaceError` otherwise.
    '''
    if not any(name in iface.function_names()
        for name in (NUM_INT_INSTANCE, NUM_INT_INSTANCE + '#')):
      raise InterfaceError(
          'the FlatCurry interface %s has no entry %s; the signature table '
          'expects the naming convention of curry-frontend 2.0.0 or 3.1.0'
              % (iface.path, NUM_INT_INSTANCE)
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
    with self._lock:
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
    entries = [(name, self._entry(module))
        for name, module in self.interp.modules.copy().items()]
    with self._lock:
      return self._instance_map(entries)

  def _instance_map(self, entries):
    for modulename, entry in entries:
      if entry.instances is not None:
        continue
      found = []
      iface = entry.interface
      if iface is not None:
        for name in iface.instance_names():
          classname, types = parse_instance_types(name, modulename)
          if len(types) != 1:
            self._unsupported_classes[classname] = len(types)
            continue
          typename = _type_name(types[0])
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
    return dict(self._instances)

  def instance(self, classname, typename):
    '''
    The :class:`Instance` of a class at a type constructor, or None.  The
    class is qualified, e.g., ``Prelude.Show``; the type constructor is
    qualified or special, e.g., ``Prelude.Maybe`` or ``[]``.
    '''
    instances = self.instances()
    if classname in self._unsupported_classes:
      unsupported_class(classname, self._unsupported_classes[classname])
    return instances.get((classname, typename))

  def instances_of(self, classname):
    '''The instances of one class, by type constructor name.'''
    return {
        typename: inst for (cls, typename), inst in self.instances().items()
                       if cls == classname
      }

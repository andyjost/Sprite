'''
The parser of ``exprtype`` strings.

The grammar is a Curry monotype without a context: type variables,
constructor names qualified or unqualified, lists, tuples, ``()``, function
arrows and parentheses.  A constructor name is resolved through the
interfaces of the loaded modules: the ``Type`` and ``TypeNew`` entries of
the FlatCurry interface give the data types and their arities, and the
``type`` declarations of the Curry interface ``M.icurry``, which travels
with the ``.fint``, give the synonyms.  The front end expands a synonym in
the interface, so one expansion suffices.

:func:`parse_type` returns a FlatCurry type whose variables are ``TVar``
with the indices of their first occurrence, and the names of the variables.
:func:`parse_term` returns the term of the engine, with one rigid variable
per name.
'''

from .. import exceptions
from ..toolchain.flat2icurry import flatcurry as fc
from .errors import (
    ContextInExprTypeError, ExprTypeSyntaxError, KindError
  , UnknownTypeConstructorError
  )
from .sigtable import PRELUDE
from .terms import APPLY, Rigid, instantiate
import os, re

__all__ = [
    'Synonym', 'icurry_filename', 'parse_term', 'parse_type', 'synonyms_of'
  ]

_TOKEN = re.compile(
    r'\s*(?:'
    r'(?P<arrow>->)|(?P<context>=>)|(?P<dcolon>::)|(?P<punct>[()\[\],])'
    r"|(?P<con>(?:[A-Z][A-Za-z0-9_']*\.)*[A-Z][A-Za-z0-9_']*)"
    r"|(?P<var>[a-z_][A-Za-z0-9_']*)"
    r'|(?P<bad>\S)'
    r')'
  )

# A synonym declaration of a Curry interface: type Name a b = rhs;
_SYNONYM = re.compile(
    r"(?m)^type\s+(?P<name>[A-Z][A-Za-z0-9_']*)"
    r"(?P<params>(?:\s+[a-z][A-Za-z0-9_']*)*)\s*=\s*(?P<rhs>[^;]*);"
  )

class Synonym:
  '''A type synonym of a module: its parameters and the text of its type.'''
  __slots__ = ('modulename', 'name', 'params', 'text')

  def __init__(self, modulename, name, params, text):
    self.modulename = modulename
    self.name = name
    self.params = tuple(params)
    self.text = ' '.join(text.split())

  @property
  def arity(self):
    return len(self.params)

  def __repr__(self):
    return '<Synonym %s.%s %s = %s>' % (
        self.modulename, self.name, ' '.join(self.params), self.text
      )

def icurry_filename(fint_filename):
  '''The Curry interface beside a FlatCurry interface.'''
  stem = fint_filename[:-len('.fint')] if fint_filename.endswith('.fint') \
      else fint_filename
  return stem + '.icurry'

# The synonyms read in this process, by file, size and time.
_SYNONYMS = {}

def synonyms_of(interp, modulename):
  '''
  The synonyms a module declares, by name, from its ``.icurry`` interface.
  An empty dict for a module without an interface.
  '''
  iface = interp.sigtable.interface(modulename)
  if iface is None:
    return {}
  path = icurry_filename(iface.path)
  try:
    st = os.stat(path)
  except OSError:
    return {}
  key = (path, st.st_size, st.st_mtime_ns)
  found = _SYNONYMS.get(key)
  if found is None:
    with open(path, 'r', encoding='utf-8') as istream:
      text = istream.read()
    found = {}
    for m in _SYNONYM.finditer(text):
      found[m.group('name')] = Synonym(
          modulename, m.group('name'), m.group('params').split(), m.group('rhs')
        )
    _SYNONYMS[key] = found
  return found

# The parser
# ==========
class _Tok:
  __slots__ = ('kind', 'text', 'column')
  def __init__(self, kind, text, column):
    self.kind = kind
    self.text = text
    self.column = column

def _tokenize(text):
  tokens = []
  pos = 0
  while pos < len(text):
    m = _TOKEN.match(text, pos)
    if m is None or m.end() == pos:
      break
    pos = m.end()
    kind = m.lastgroup
    if kind is None:
      break
    column = m.start(kind) + 1
    if kind == 'context':
      raise ContextInExprTypeError(text)
    if kind == 'bad' or kind == 'dcolon':
      raise ExprTypeSyntaxError(text, 'unexpected %r' % m.group(kind), column)
    tokens.append(_Tok(kind, m.group(kind), column))
  tokens.append(_Tok('end', '', len(text) + 1))
  return tokens

class _Parser:
  '''
  A recursive-descent parser over the tokens.  It produces a FlatCurry type
  with ``TVar`` leaves and resolves constructor names through ``env``.
  '''
  def __init__(self, text, env, names):
    self.text = text
    self.env = env
    self.tokens = _tokenize(text)
    self.pos = 0
    self.names = names  # variable name -> index

  def peek(self):
    return self.tokens[self.pos]

  def take(self):
    tok = self.tokens[self.pos]
    self.pos += 1
    return tok

  def fail(self, reason, tok=None):
    tok = self.peek() if tok is None else tok
    raise ExprTypeSyntaxError(self.text, reason, tok.column)

  def expect(self, text):
    tok = self.take()
    if tok.text != text:
      what = 'end of text' if tok.kind == 'end' else repr(tok.text)
      self.fail('expected %r, found %s' % (text, what), tok)

  def parse(self):
    t = self.type_(root=True)
    tok = self.peek()
    if tok.kind != 'end':
      self.fail('unexpected %r' % tok.text)
    return t

  def type_(self, root=False):
    t = self.btype(root)
    if self.peek().kind == 'arrow':
      self.take()
      return fc.FuncType(t, self.type_(root))
    return t

  def btype(self, root=False):
    '''An application: a head and its arguments.'''
    tok = self.peek()
    if tok.kind == 'end' or tok.text in (')', ']', ','):
      what = 'end of text' if tok.kind == 'end' else repr(tok.text)
      self.fail('expected a type, found %s' % what)
    head_tok = self.take()
    if head_tok.kind == 'con':
      return self.constructor(head_tok, self.arguments(), root)
    head = self.atype(head_tok)
    args = self.arguments()
    if not args:
      return head
    if isinstance(head, fc.TVar) \
        or (isinstance(head, fc.TCons) and head.name == APPLY):
      for arg in args:
        head = fc.TCons(APPLY, [head, arg])
      return head
    self.fail('%r takes no type argument' % head_tok.text, head_tok)

  def arguments(self):
    '''The argument types of an application, each without application.'''
    args = []
    while self.peek().kind in ('con', 'var') or self.peek().text in ('(', '['):
      args.append(self.atype(self.take()))
    return args

  def atype(self, tok):
    '''A type without application: the token ``tok`` starts it.'''
    if tok.kind == 'var':
      index = self.names.get(tok.text)
      if index is None:
        index = self.names[tok.text] = len(self.names)
      return fc.TVar(index)
    if tok.kind == 'con':
      return self.constructor(tok, [], False)
    if tok.text == '(':
      if self.peek().text == ')':
        self.take()
        return fc.TCons(fc.prelude('()'), [])
      items = [self.type_()]
      while self.peek().text == ',':
        self.take()
        items.append(self.type_())
      self.expect(')')
      if len(items) == 1:
        return items[0]
      return fc.TCons(fc.prelude('(%s)' % (',' * (len(items) - 1))), items)
    if tok.text == '[':
      if self.peek().text == ']':
        self.take()
        return fc.TCons(fc.prelude('[]'), [])
      item = self.type_()
      self.expect(']')
      return fc.TCons(fc.prelude('[]'), [item])
    what = 'end of text' if tok.kind == 'end' else repr(tok.text)
    self.fail('expected a type, found %s' % what, tok)

  def constructor(self, tok, args, root):
    '''A constructor applied to ``args``; a synonym is expanded.'''
    entry = self.env.lookup(tok.text, self.text)
    if isinstance(entry, Synonym):
      if len(args) != entry.arity:
        raise KindError(tok.text, entry.arity, len(args), self.text)
      return self.env.expand(entry, args)
    qname, arity = entry
    if len(args) > arity or (root and len(args) < arity):
      raise KindError(tok.text, arity, len(args), self.text)
    return fc.TCons(qname, args)

class _Env:
  '''Resolves constructor names through the loaded modules.'''

  def __init__(self, interp, module=None):
    self.interp = interp
    self.table = interp.sigtable
    self.module = module
    self.depth = 0

  def modules(self):
    '''The search order: the context module, the Prelude, the rest.'''
    names = []
    if self.module is not None:
      names.append(self.module)
    names.append(PRELUDE)
    names.extend(self.interp.modules)
    return list(dict.fromkeys(names))

  def entry(self, modulename, name):
    '''A data type as ``(qname, arity)``, a :class:`Synonym`, or None.'''
    try:
      iface = self.table.interface(modulename)
    except exceptions.ModuleLookupError:
      return None
    if iface is None:
      return None
    decl = iface.type_decl(name)
    if decl is not None and not isinstance(decl, fc.TypeSyn):
      return ((modulename, name), len(decl.typevars))
    return synonyms_of(self.interp, modulename).get(name)

  def searched(self):
    return [m for m in self.modules() if self.table.interface(m) is not None]

  def lookup(self, text, source):
    if '.' in text:
      modulename, _, name = text.rpartition('.')
      if modulename not in self.interp.modules:
        raise UnknownTypeConstructorError(
            text, self.searched(), source
          , detail='the module %s is not loaded' % modulename
          )
      entry = self.entry(modulename, name)
      if entry is None:
        raise UnknownTypeConstructorError(text, [modulename], source)
      return entry
    found = []
    for modulename in self.modules():
      entry = self.entry(modulename, text)
      if entry is not None:
        found.append((modulename, entry))
    if not found:
      raise UnknownTypeConstructorError(text, self.searched(), source)
    if len(found) > 1 and self.module is None:
      raise UnknownTypeConstructorError(
          text, self.searched(), source
        , detail='the name is declared in %s; qualify it'
              % ' and '.join(m for m, _ in found)
        )
    return found[0][1]

  def expand(self, synonym, args):
    '''The type of a synonym applied to ``args``.'''
    if self.depth > 50:
      raise KindError(synonym.name, synonym.arity, len(args), synonym.text)
    env = _Env(self.interp, synonym.modulename)
    env.depth = self.depth + 1
    names = {param: i for i, param in enumerate(synonym.params)}
    body = _Parser(synonym.text, env, names).parse()
    mapping = dict(zip(range(len(args)), args))
    return _substitute(body, mapping)

def _substitute(typeexpr, mapping):
  if isinstance(typeexpr, fc.TVar):
    return mapping.get(typeexpr.index, typeexpr)
  if isinstance(typeexpr, fc.FuncType):
    return fc.FuncType(
        _substitute(typeexpr.domain, mapping), _substitute(typeexpr.range, mapping)
      )
  if isinstance(typeexpr, fc.TCons):
    return fc.TCons(typeexpr.name, [_substitute(a, mapping) for a in typeexpr.args])
  return typeexpr

def parse_type(interp, text, module=None):
  '''
  Parses an ``exprtype`` string.

  Args:
    interp:
        The interpreter whose loaded modules resolve the names.
    text:
        The type in Curry syntax, without a context.
    module:
        The module whose names are preferred for an unqualified name, or
        None.

  Returns:
    A pair: the FlatCurry type, whose variables are ``TVar`` with the
    indices of their first occurrence, and a dict from index to name.

  Raises:
    ExprTypeSyntaxError, ContextInExprTypeError, KindError,
    UnknownTypeConstructorError
  '''
  names = {}
  typeexpr = _Parser(text, _Env(interp, module), names).parse()
  return typeexpr, {index: name for name, index in names.items()}

def parse_term(interp, text, module=None):
  '''
  Parses an ``exprtype`` string into a term of the engine.  Each type
  variable becomes one :class:`Rigid <curry.typecheck.terms.Rigid>`.
  '''
  typeexpr, names = parse_type(interp, text, module)
  mapping = {index: Rigid(name, text) for index, name in names.items()}
  return instantiate(typeexpr, mapping)

'''
Encoding of Curry identifiers.
'''

from .. import inspect
import collections, itertools, keyword, logging, re, six

logger = logging.getLogger(__name__)

__all__ = ['best', 'clean', 'encode', 'isaCurryIdentifier', 'symbolToFilename']

P_SYMBOL = re.compile('[^0-9a-zA-Z_\s]')
TR = {
    '&' : '_amp_'
  , '@' : '_at_'
  , '!' : '_bang_'
  , '`' : '_bt_'
  , '^' : '_car_'
  , ':' : '_col_'
  , ',' : '_com_'
  , '$' : '_dolr_'
  , '.' : '_dot_'
  , '"' : '_dq_'
  , '=' : '_eq_'
  , '\\ ': '_esc_'
  , '>' : '_gt_'
  , '{' : '_lbc_'
  , '[' : '_lbk_'
  , '(' : '_lp_'
  , '<' : '_lt_'
  , '-' : '_neg_'
  , '#' : '_hsh_'
  , '%' : '_pct_'
  , '|' : '_pipe_'
  , '+' : '_pos_'
  , '?' : '_q_'
  , '}' : '_rbc_'
  , ']' : '_rbk_'
  , ')' : '_rp_'
  , ';' : '_semi_'
  , '/' : '_sep_'
  , '\'': '_sq_'
  , '*' : '_star_'
  , '~' : '_til_'
  }

SPECIAL = {
    '(->)' : 'Arrow'
  , '[]'   : 'Nil'
  , ':'    : 'Cons'
  , '?'    : 'Choice'
  , '()'   : 'Unit'
  , '(,)'  : 'Pair'
  , '(,,)' : 'Triple'
  , '&&'   : 'and'
  , '||'   : 'or'
  , '&'    : 'bitand'
  , '|'    : 'bitor'
  , '^'    : 'bitxor'
  , '.'    : 'compose'
  , '=:='  : 'constrEqOp'
  , '=:<=' : 'nonstrictEqOp'
  , '=:<<=': 'unifEqLinearOp'
  , '==='  : 'eq3'
  , '=='   : 'eq'
  , '/='   : 'ne'
  , '<'    : 'lt'
  , '>'    : 'gt'
  , '<='   : 'le'
  , '>='   : 'ge'
  , '+'    : 'add'
  , '-'    : 'sub'
  , '*'    : 'mul'
  , '/'    : 'div'
  , '%'    : 'mod'
  , '>>'   : 'rsh'
  , '<<'   : 'lsh'
  , '>>='  : 'irsh'
  , '<<='  : 'ilsh'
  , '++'   : 'append'
  , '**'   : 'pow'
  , '<*>'  : 'ufo'
  , '<|>'  : 'alt'
  }

P_TRAILING = re.compile('(\S+)(_CASE\d+)')
def specialName(s):
  if s in SPECIAL:
    return SPECIAL[s]
  elif inspect.isa_tuple_name(s):
    return 'Tuple%s' % (s.count(',') + 1)
  elif s.startswith('Prelude.'):
    return specialName(s[8:])
  else:
    m = re.match(P_TRAILING, s)
    if m:
      front, back = m.groups()
      special = specialName(front)
      if special:
        return special + back

def best(prefix, thing, disallow, limit=40):
  '''
  Choose the best name for something.

  This is more art than science.  Every name must be unique and must be a valid
  Python identifier.  Names should be as short and easy to read as possible.
  Some context (i.e., the module or package name) is helpful unless the name
  gets too long.  Names need not be deterministic.
  '''
  if isinstance(thing, str):
    def stems():
      yield thing
      yield _shortername(thing)
  else:
    def stems():
      yield getattr(thing, 'fullname', None)
      yield getattr(thing, 'name', None)
      yield getattr(thing, '__name__', None)
      yield _shortername(getattr(thing, 'name', None))
      yield _shortrepr(thing)
  for stem in stems():
    if stem is not None:
      best = encode(stem, prefix, disallow)
      if len(best) <= limit:
        return best
  else:
    try:
      h = hash(thing)
    except TypeError:
      h = hash(best)
    best = encode(hex(h & 0xffff), prefix, disallow)

  assert len(best) <= limit
  return best


def clean(s, dot_as_us=True):
  '''Clean up a string by encoding or removing illegal characters.'''
  special = specialName(s)
  if special:
    return special
  elif s.startswith('Prelude.'):
    tailname = s[8:]
    if isaTypeclassIdentifier(tailname):
      name = '_'.join(map(clean, tailname.split('#')[1:]))
      return clean(name, dot_as_us)
    else:
      return clean(tailname, dot_as_us)
  else:
    if dot_as_us:
      s = s.replace('.', '_')
    a = ''.join(TR.get(ch, ch) for ch in s)
    return str(re.sub(P_SYMBOL, '', a))

def encode(name, prefix='', disallow={}):
  '''
  Encode a Curry name into a legal Python identifier.

  Parameters:
  -----------
  ``name``
      The Curry identifier to encode.
  ``disallow``
      A container of disallowed names.

  Returns:
  --------
  A string holding the encoded identifier.
  '''
  a = clean(name)
  k = '%s%s' % (prefix, a)
  if k in disallow or keyword.iskeyword(k):
    # Append a number.
    k_ = k
    i = itertools.count()
    while k_ in disallow or keyword.iskeyword(k_):
      k_ = '%s_%d' % (k, next(i))
    k = k_
  assert k not in disallow
  assert k.startswith(prefix)
  return k

def _shortername(name):
  if name is not None:
    parts = name.split('.')
    for i in reversed(range(len(parts))):
      if isaCurryIdentifier(parts[i]):
        return '.'.join(parts[i:])

def _shortrepr(obj):
  if not isinstance(obj, six.string_types):
    if isinstance(obj, collections.Sequence):
      return '_'.join(map(str, obj))
    else:
      return repr(obj)

def symbolToFilename(name):
  '''Makes the given symbol name into a valid UNIX filename.'''
  assert name not in ['.', '..']
  return ''.join(TR.get('/') if ch=='/' else ch for ch in name)

# Fixme: This does not match names such as a'.
P_IDENTIFIER = re.compile('^[a-zA-Z_][0-9a-zA-Z_]*$|^[^0-9a-zA-Z_\s]+$')
def isaCurryIdentifier(basename):
  '''
  Indicates whether the given string is a valid Curry identifier.  Legal
  identifiers are 1) strings not beginning with a number where each character
  is alphanumeric or an underscore; and 2) strings comprising only
  non-alphanumeric, non-underscore, non-whitespace characters.
  '''
  return bool(re.match(P_IDENTIFIER, basename))

P_TYPECLASS_KEYS = re.compile('^_(def|Dict|impl|inst|super)#')
def isaTypeclassIdentifier(basename):
  return bool(re.match(P_TYPECLASS_KEYS, basename))


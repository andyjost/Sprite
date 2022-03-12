import collections

# Symbol kind.
DATA_TYPE      = 'DATA_TYPE'   # A Curry data type (for narrowing).
INFO_TABLE     = 'INFO_TABLE'  # Constructor or Function info table.
STRING_DATA    = 'STRING_DATA' # Static string data.
VALUE_SET      = 'VALUE_SET'   # Case values (for narrowing).
STEP_FUNCTION  = 'LOCAL_FUNC'  # A step function.
#                 ^ first letters need to be unique for symbol encoding.

# Symbol status.
DEFINED   = 'T'
UNDEFINED = 'U'

Symbol = collections.namedtuple(
    'Symbol', ['tgtname', 'stat', 'kind', 'srcname']
  )

def mangle(splitname, kind):
  # E.g., Prelude.: -> _YI7Prelude5_col_
  #    _Y       = prefix for Curry symbol
  #    I        = symbol kind (info table)
  #    7Prelude = name qualifier
  #    5_col_   = encoded name

  parts = splitname[:-1] + [encoding.encode(splitname[-1])]
  code = kind[0]
  head = '_Y%s%s' % (kind[0], ''.join('%s%s' % (len(p), p) for p in parts))


# E.g.: the symbol for Prelude.: might appear in the symbol table for the
# Prelude as follows:
#
#   ('_Y7Prelude4Cons', 'T', INFO_TABLE, 'Prelude.:')


class SymbolTable(object):
  def __init__(self):
    self._data = {}  # {str: Symbol}

  def lookup(self, obj, kind):
    tgtname = mangle(obj.splitname(), kind)
    symbol = Symbol(tgtname, UNDEFINED, kind, obj.fullname)
    self._data.setdefault(tgtname, symbol)
    return tgtname, self._data[tgtname]

  def use(obj, kind):
    tgtname, _ = self.lookup(obj, kind)
    return tgtname

  def defined(obj, kind):
    
    tgtname, slot = self.lookup(obj, kind)



    symbol = self.update_referenced(obj, kind)

    tgtname = mangle(obj.splitname(), kind)
    symbol = Symbol(tgtname, DEFINED, kind, obj.fullname)
    self._data.setdefault(tgtname, symbol)

#   def _key(self, key):
#     # Accepts Symbol or str.
#     tgtname = getattr(key, 'tgtname', key)
#     return str(tgtname)
#   
#   def setdefault(self, key)
#   def update(self, arg)
#   def get(self, key)
#   def popitem(self, key)
# 
#   def __contains__(self, key)
#   def __delitem__(self, key)
# 
# 
# 
#   def find_or_insert(symbol):
#     assert isinstance(symbol, Symbol)
#     self._data[symbol.name] = symbol
# 

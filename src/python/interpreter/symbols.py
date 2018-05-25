'''
Code for working with symbols.
'''

import itertools
import re

class SymbolLookupError(AttributeError):
  '''Raised when a Curry symbol is not found.'''

SYMBOL_CHAR = re.compile('[^0-9a-zA-Z_ ]')
IDENTIFIER = re.compile('^[a-zA-Z_][0-9a-zA-Z_]*$|^[^0-9a-zA-Z_ ]+$')
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

def clean(s):
  '''Clean up a string by encoding or removing illegal characters.'''
  a = ''.join(TR.get(ch, ch) for ch in s)
  return str(re.sub(SYMBOL_CHAR, '', a))

def encode(iname, disallow={}):
  '''
  Encode an ``icurry.IName`` into a legal Python identifier.

  Parameters:
  -----------
  ``iname``
      The Curry identifier to encode.
  ``disallow``
      A container of disallowed names.

  Returns:
  --------
  A string holding the encoded identifier.
  '''
  # First, try just the basename.
  a = clean(iname.basename)
  k = 'ti_%s' % a
  if k in disallow:
    # If it conflicts, try prepending the module name.
    k = 'ti_%s_%s' % (clean(iname.module), a)
    if k in disallow:
      # Finally, append a number.
      k_ = k
      i = itertools.count()
      while k_ in disallow:
        k_ = '%s_%d' % (k, next(i))
      k = k_
  assert k not in disallow
  assert k.startswith('ti_')
  return k

def isaCurryIdentifier(basename):
  '''
  Indicates whether the given string is a valid Curry identifier.  Legal identifiers
  are strings containing alphanumeric 
  '''
  return bool(re.match(IDENTIFIER, basename))
  
# FIXME: ICurry does not tell us which symbols are private.  For now, all
# symbols are treated as public.
def insert(module, basename, typeinfo, private=False):
  '''
  Inserts a symbol into the given module.

  All symbols are added to the module's '.symbols' dict.  Public symbols are
  also bound directly to the module itself.

  Parameters:
  -----------
  ``module``
      An instance of ``CurryModule``.
  ``basename``
      A stirng containing the unqualified symbol name.
  ``typeinfo``
      The typeinfo for this symbol.
  ``private``
      Whether this is a private symbol.

  Returns:
  --------
  Nothing.
  '''
  getattr(module, '.symbols')[basename] = typeinfo
  if not private and isaCurryIdentifier(basename):
    setattr(module, basename, typeinfo)

def lookupSymbol(module, iname):
  '''
  Looks up a symbol in the given module.
  '''
  symbols = getattr(module, '.symbols')
  try:
    return symbols[iname.basename]
  except KeyError:
    raise SymbolLookupError(
        'module "%s" has no symbol "%s"' % (iname.module, iname.basename)
      )

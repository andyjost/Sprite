'''
Encoding of Curry identifiers.
'''

import itertools
import logging
import re

logger = logging.getLogger(__name__)

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
    'Prelude.[]' : 'Nil'
  , 'Prelude.:'  : 'Cons'
  , 'Prelude.?'  : 'Choice'
  , 'Prelude.()' : 'Unit'
  , 'Prelude.&&' : 'and'
  , 'Prelude.||' : 'or'
  , 'Prelude.==' : 'eq'
  , 'Prelude./=' : 'ne'
  , 'Prelude.<'  : 'lt'
  , 'Prelude.>'  : 'gt'
  , 'Prelude.<=' : 'le'
  , 'Prelude.>=' : 'ge'
  , 'Prelude.+'  : 'add'
  , 'Prelude.-'  : 'sub'
  , 'Prelude.*'  : 'mul'
  , 'Prelude./'  : 'div'
  , 'Prelude.%'  : 'mod'
  , 'Prelude.^'  : 'pow'
  }

def clean(s):
  '''Clean up a string by encoding or removing illegal characters.'''
  if s in SPECIAL:
    return SPECIAL[s]
  elif s.startswith('Prelude.'):
    return clean(s[8:])
  else:
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
  if k in disallow:
    # Append a number.
    k_ = k
    i = itertools.count()
    while k_ in disallow:
      k_ = '%s_%d' % (k, next(i))
    k = k_
  assert k not in disallow
  assert k.startswith(prefix)
  return k

def symbolToFilename(name):
  '''Makes the given symbol name into a valid UNIX filename.'''
  assert name not in ['.', '..']
  return ''.join(TR.get('/') if ch=='/' else ch for ch in name)

P_IDENTIFIER = re.compile('^[a-zA-Z_][0-9a-zA-Z_]*$|^[^0-9a-zA-Z_\s]+$')
def isaCurryIdentifier(basename):
  '''
  Indicates whether the given string is a valid Curry identifier.  Legal
  identifiers are 1) strings not beginning with a number where each character
  is alphanumeric or an underscore; and 2) strings comprising only
  non-alphanumeric, non-underscore, non-whitespace characters.
  '''
  return bool(re.match(P_IDENTIFIER, basename))


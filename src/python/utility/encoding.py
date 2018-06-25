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

def clean(s):
  '''Clean up a string by encoding or removing illegal characters.'''
  a = ''.join(TR.get(ch, ch) for ch in s)
  return str(re.sub(P_SYMBOL, '', a))

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
  k = 'ni_%s' % a
  if k in disallow:
    # If it conflicts, try prepending the module name.
    k = 'ni_%s_%s' % (clean(iname.module), a)
    if k in disallow:
      # Finally, append a number.
      k_ = k
      i = itertools.count()
      while k_ in disallow:
        k_ = '%s_%d' % (k, next(i))
      k = k_
  assert k not in disallow
  assert k.startswith('ni_')
  return k

def symbolToFilename(iname):
  '''Makes the given symbol name into a valid UNIX filename.'''
  assert iname not in ['.', '..']
  return ''.join(TR.get('/') if ch=='/' else ch for ch in iname)

P_IDENTIFIER = re.compile('^[a-zA-Z_][0-9a-zA-Z_]*$|^[^0-9a-zA-Z_\s]+$')
def isaCurryIdentifier(basename):
  '''
  Indicates whether the given string is a valid Curry identifier.  Legal
  identifiers are 1) strings not beginning with a number where each character
  is alphanumeric or an underscore; and 2) strings comprising only
  non-alphanumeric, non-underscore, non-whitespace characters.
  '''
  return bool(re.match(P_IDENTIFIER, basename))


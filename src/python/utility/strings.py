from six import PY2, PY3, text_type, binary_type

def ensure_str_safe(arg, encoding='utf-8', errors='strict'):
  '''Like ensure_str, but passes non-string-like objects through.'''
  if isinstance(arg, (text_type, binary_type)):
    return ensure_str(arg, encoding, errors)
  else:
    return arg

def ensure_binary_safe(arg, encoding='utf-8', errors='strict'):
  '''Like ensure_binary, but passes non-string-like objects through.'''
  if isinstance(arg, (text_type, binary_type)):
    return ensure_binary(arg, encoding, errors)
  else:
    return arg

def ensure_text_safe(arg, encoding='utf-8', errors='strict'):
  '''Like ensure_text, but passes non-string-like objects through.'''
  if isinstance(arg, (text_type, binary_type)):
    return ensure_text(arg, encoding, errors)
  else:
    return arg

try:
  from six import ensure_str
except ImportError:
  def ensure_str(s, encoding='utf-8', errors='strict'):
    """Coerce *s* to `str`.

    For Python 2:
      - `unicode` -> encoded to `str`
      - `str` -> `str`

    For Python 3:
      - `str` -> `str`
      - `bytes` -> decoded to `str`
    """
    # Optimization: Fast return for the common case.
    if type(s) is str:
      return s
    if PY2 and isinstance(s, text_type):
      return s.encode(encoding, errors)
    elif PY3 and isinstance(s, binary_type):
      return s.decode(encoding, errors)
    elif not isinstance(s, (text_type, binary_type)):
      raise TypeError("not expecting type '%s'" % type(s))
    return s

try:
  from six import ensure_binary
except ImportError:
  def ensure_binary(s, encoding='utf-8', errors='strict'):
    """Coerce **s** to six.binary_type.

    For Python 2:
      - `unicode` -> encoded to `str`
      - `str` -> `str`

    For Python 3:
      - `str` -> encoded to `bytes`
      - `bytes` -> `bytes`
    """
    if isinstance(s, binary_type):
      return s
    if isinstance(s, text_type):
      return s.encode(encoding, errors)
    raise TypeError("not expecting type '%s'" % type(s))

try:
  from six import ensure_text
except ImportError:
  def ensure_text(s, encoding='utf-8', errors='strict'):
    """Coerce *s* to six.text_type.

    For Python 2:
      - `unicode` -> `unicode`
      - `str` -> `unicode`

    For Python 3:
      - `str` -> `str`
      - `bytes` -> decoded to `str`
    """
    if isinstance(s, binary_type):
      return s.decode(encoding, errors)
    elif isinstance(s, text_type):
      return s
    else:
      raise TypeError("not expecting type '%s'" % type(s))


def ensure_str_safe(arg, encoding='utf-8', errors='strict'):
  '''Like ensure_str, but passes non-string-like objects through.'''
  if isinstance(arg, (str, bytes)):
    return ensure_str(arg, encoding, errors)
  else:
    return arg

def ensure_binary_safe(arg, encoding='utf-8', errors='strict'):
  '''Like ensure_binary, but passes non-string-like objects through.'''
  if isinstance(arg, (str, bytes)):
    return ensure_binary(arg, encoding, errors)
  else:
    return arg

def ensure_text_safe(arg, encoding='utf-8', errors='strict'):
  '''Like ensure_text, but passes non-string-like objects through.'''
  if isinstance(arg, (str, bytes)):
    return ensure_text(arg, encoding, errors)
  else:
    return arg

def ensure_str(s, encoding='utf-8', errors='strict'):
  """Coerce *s* to `str`.

    - `str` -> `str`
    - `bytes` -> decoded to `str`
  """
  # Optimization: Fast return for the common case.
  if type(s) is str:
    return s
  if isinstance(s, bytes):
    return s.decode(encoding, errors)
  elif not isinstance(s, str):
    raise TypeError("not expecting type '%s'" % type(s))
  return s

def ensure_binary(s, encoding='utf-8', errors='strict'):
  """Coerce **s** to `bytes`.

    - `str` -> encoded to `bytes`
    - `bytes` -> `bytes`
  """
  if isinstance(s, bytes):
    return s
  if isinstance(s, str):
    return s.encode(encoding, errors)
  raise TypeError("not expecting type '%s'" % type(s))

def ensure_text(s, encoding='utf-8', errors='strict'):
  """Coerce *s* to `str`.

    - `str` -> `str`
    - `bytes` -> decoded to `str`
  """
  if isinstance(s, bytes):
    return s.decode(encoding, errors)
  elif isinstance(s, str):
    return s
  else:
    raise TypeError("not expecting type '%s'" % type(s))

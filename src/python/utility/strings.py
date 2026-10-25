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

def int_text(value):
  '''Decimal digits of an Int without changing Python's process digit limit.'''
  try:
    return str(value)
  except ValueError:
    # Python bounds decimal conversions for untrusted text. Curry Ints are
    # already integers; convert in chunks below Python's minimum limit.
    negative = value < 0
    value = abs(value)
    parts = []
    while value:
      value, part = divmod(value, 10 ** 500)
      parts.append(part)
    text = str(parts.pop()) if parts else '0'
    text += ''.join('%0500d' % part for part in reversed(parts))
    return '-' + text if negative else text

def parse_int(text):
  '''Read exact decimal Int digits without a process-wide setting change.'''
  if not isinstance(text, str):
    return int(text)
  negative = text.startswith('-')
  digits = text[1:] if text.startswith(('-', '+')) else text
  if len(digits) <= 500 or not (digits.isascii() and digits.isdigit()):
    return int(text)
  value = 0
  for start in range(0, len(digits), 500):
    chunk = digits[start:start+500]
    value = value * 10 ** len(chunk) + int(chunk)
  return -value if negative else value

import contextlib

del_ = object()

@contextlib.contextmanager
def binding(mapping, key, value):
  '''
  Context manager that temporarily binds a value in some mapping.

  Parameters:
  -----------
  ``mapping``
      The mapping to modify.
  ``key``
      The key indicating which item to modify.
  ``value``
      The temporary value to use, or the special object ``del_``.

  Returns:
  --------
  A context manager within which ``mapping[key]`` will be bound to ``value``.
  If value is ``del_``, then the element will be deleted.  The original state
  will be restored when exiting the context.
  '''
  prev = mapping.get(key, del_)
  if value is del_:
    try:
      del mapping[key]
    except KeyError:
      pass
  else:
    mapping[key] = value
  try:
    yield
  finally:
    if prev is del_:
      try:
        del mapping[key]
      except KeyError:
        pass
    else:
      mapping[key] = prev


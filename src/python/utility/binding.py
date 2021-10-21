
del_ = object()

class Binding(object):
  def __init__(self, mapping, key, value):
    self.committed = False
    self.key = key
    self.mapping = mapping
    self.value = value

  def commit(self):
    self.committed = True

  def __enter__(self):
    self.prev = self.mapping.get(self.key, del_)
    if self.value is del_:
      try:
        del self.mapping[self.key]
      except KeyError:
        pass
    else:
      self.mapping[self.key] = self.value
    return self

  def __exit__(self, *args):
    if not self.committed:
      if self.prev is del_:
        try:
          del self.mapping[self.key]
        except KeyError:
          pass
      else:
        self.mapping[self.key] = self.prev


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
  return Binding(mapping, key, value)


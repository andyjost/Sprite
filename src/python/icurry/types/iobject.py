from ...utility import curryname
from ...utility.proptree import proptree
import collections, six, weakref

__all__ = ['IArity', 'IObject', 'IVarIndex']

IArity = int
IVarIndex = int

class IObject(object):
  def __init__(self, metadata=None):
    if metadata is not None:
      self._metadata = proptree(metadata)

  @property
  def metadata(self):
    return getattr(self, '_metadata', {})

  def update_metadata(self, items):
    md = getattr(self.metadata, '_asdict', self.metadata)
    md.update(items)
    self._metadata = proptree(md)

  @property
  def children(self):
    return ()

  def copy(self, **updates):
    '''Copy an IObject with optional updates.'''
    data = self.dict()
    data.update(**updates)
    return type(self)(**data)

  def dict(self):
    '''Get the object properties as a dictionary.'''
    if hasattr(self, '_fields_'):
      return collections.OrderedDict(
         (name, getattr(self, name)) for name in self._fields_
       )
    else:
      return {
          k:v for k,v in six.iteritems(self.__dict__)
              if k != 'metadata'
        }

  # Make objects comparable by their contents.
  def __eq__(lhs, rhs):
    if rhs is None:
      return False
    if type(lhs) != type(rhs):
      return False

    # Compare dicts.
    return lhs.dict() == rhs.dict()

  def __ne__(lhs, rhs):
    return not (lhs == rhs)

  def __hash__(self):
    return hash(tuple(sorted(self.dict())))

  def __repr__(self):
    return '%s(%s)' % (
        type(self).__name__
      , ', '.join(
            '%s=%r' % item for item in self.dict().items()
          )
      )

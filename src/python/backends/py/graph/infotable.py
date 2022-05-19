from .... import backends, common
import weakref

class DataType(object):
  def __init__(self, name, ctorinfos):
    self.name = name
    self._ctorinfos = tuple(ctorinfos)
    for ctorinfo in ctorinfos:
      assert ctorinfo.typedef is None
      ctorinfo.typedef = self

  @property
  def constructors(self):
    return self._ctorinfos


class InfoTable(object):
  '''
  Runtime info for a node.  Every Curry node stores an `InfoTable`` instance,
  which contains instance-independent data.
  '''
  _fields_ = ['name', 'arity', 'tag', 'flags', 'step', 'typedef', 'pyformat']

  def __init__(self, name, arity, tag, flags, step, pyformat):
    self.name = name
    self.arity = arity
    self.tag = tag
    self.flags = flags
    self._step = step
    # The type that this constructor belongs to.  This is needed at runtime to
    # implement =:=, when a free variable must be bound to an HNF.  It could be
    # improved to use just a runtime version of the typeinfo.
    self._typedef = None

    # PYTHON-SPECIFIC:

    # Describes the node format.  It must have a ``format`` method, which will
    # be passed the node name followed by its rendered arguments.
    self.pyformat = pyformat

  def __str__(self):
    return 'Info for %r' % self.name

  def __repr__(self):
    show = lambda x: repr(x()) if isinstance(x, weakref.ref) else repr(x)
    return ''.join([
        'InfoTable('
      , ', '.join(
            '%s=%s' % (field, show(getattr(self, field)))
                for field in self._fields_
          )
      , ')'
      ])

  @property
  def typedef(self):
    return None if self._typedef is None else self._typedef()

  @typedef.setter
  def typedef(self, value):
    self._typedef = weakref.ref(value)

  @property
  def typetag(self):
    return self.flags & 0xf

  @property
  def step(self):
    if hasattr(self._step, 'materialize'):
      self._step = self._step.materialize()
    return self._step

  @step.setter
  def step(self, value):
    self._step = value

  @property
  def is_special(self):
    return self.flags & 0xf

  @property
  def is_primitive(self):
    return self.typetag in \
        [common.F_INT_TYPE, common.F_CHAR_TYPE, common.F_FLOAT_TYPE]

  @property
  def is_int(self):
    return self.typetag == common.F_INT_TYPE

  @property
  def is_char(self):
    return self.typetag == common.F_CHAR_TYPE

  @property
  def is_float(self):
    return self.typetag == common.F_FLOAT_TYPE

  @property
  def is_bool(self):
    return self.typetag == common.F_BOOL_TYPE

  @property
  def is_list(self):
    return self.typetag == common.F_LIST_TYPE

  @property
  def is_tuple(self):
    return self.typetag == common.F_TUPLE_TYPE

  @property
  def is_io(self):
    return self.typetag == common.F_IO_TYPE

  @property
  def is_partial(self):
    return self.typetag == common.F_PARTIAL_TYPE

  @property
  def is_monadic(self):
    return self.flags & common.F_MONADIC

  @property
  def is_operator(self):
    return self.flags & common.F_OPERATOR

backends.InfoTable.register(InfoTable)

from . import types
from ..utility.fmap import fmap
from ..utility.strings import ensure_str_safe, ensure_str, int_text
from ..utility.visitation import dispatch
from ..utility.trampoline import trampoline
import collections, json, traceback

def _object_hook(kwds):
  try:
    clsname = kwds.pop('__class__')
  except KeyError:
    return kwds

  try:
    cls = types.__dict__[clsname]
  except KeyError:
    raise TypeError('No ICurry class named %s was found' % clsname)

  try:
    kwds = fmap(ensure_str_safe, kwds)
    return cls(**kwds)
  except Exception:
    raise TypeError(
        'Cannot construct %s.%s from arguments %r: %s'
            % (cls.__module__, cls.__name__, kwds, traceback.format_exc())
      )

def get_decoder():
  return Decoder(object_hook=_object_hook)

class Decoder(json.JSONDecoder):
  '''Read containers on a heap stack; the standard decoder reads scalars.'''
  def decode(self, text):
    value, end = trampoline(self._value(text, 0))
    end = json.decoder.WHITESPACE.match(text, end).end()
    if end != len(text):
      raise json.JSONDecodeError('Extra data', text, end)
    return value

  def _value(self, text, pos):
    pos = json.decoder.WHITESPACE.match(text, pos).end()
    if pos == len(text) or text[pos] not in '[{':
      return self.raw_decode(text, pos)
    mapping = text[pos] == '{'
    close = '}' if mapping else ']'
    result = {} if mapping else []
    pos = json.decoder.WHITESPACE.match(text, pos + 1).end()
    if text[pos:pos+1] == close:
      value = self.object_hook(result) if mapping and self.object_hook else result
      return value, pos + 1
    while True:
      if mapping:
        if text[pos:pos+1] != '"':
          raise json.JSONDecodeError('Expecting property name', text, pos)
        key, pos = self.raw_decode(text, pos)
        pos = json.decoder.WHITESPACE.match(text, pos).end()
        if text[pos:pos+1] != ':':
          raise json.JSONDecodeError("Expecting ':' delimiter", text, pos)
        pos += 1
      value, pos = yield self._value(text, pos)
      if mapping:
        result[key] = value
      else:
        result.append(value)
      pos = json.decoder.WHITESPACE.match(text, pos).end()
      if text[pos:pos+1] == close:
        value = self.object_hook(result) if mapping and self.object_hook else result
        return value, pos + 1
      if text[pos:pos+1] != ',':
        raise json.JSONDecodeError("Expecting ',' delimiter", text, pos)
      pos = json.decoder.WHITESPACE.match(text, pos + 1).end()

def loads(json, decoder=get_decoder()):
  '''Load ICurry encoded as JSON.'''
  icurry = decoder.decode(ensure_str(json))
  return icurry

def load(file, decoder=get_decoder()):
  if isinstance(file, str):
    with open(file, 'r', encoding='utf-8') as istream:
      data = istream.read()
    return loads(data)
  else:
    return loads(file.read())

def get_encoder(compact=True):
  return Encoder(compact=compact)

class Encoder(json.JSONEncoder):
  '''
  Encodes ICurry as JSON.

  The compact form, the default, has no space after a comma or a colon.  Both
  forms escape every character outside ASCII.  The toolchain writes the
  compact form into the ``.json.z`` caches.
  '''
  def __init__(self, compact=True, **kwds):
    if compact:
      kwds.setdefault('separators', (',', ':'))
    json.JSONEncoder.__init__(self, **kwds)

  def iterencode(self, obj, _one_shot=False):
    # Each item is a value to expand, literal text, or an ancestor to leave.
    # Keep circular-reference detection, including default() conversions.
    stack = [('value', obj, 0)]
    indent = self.indent
    if indent is not None and not isinstance(indent, str):
      indent = ' ' * indent
    active = set()
    scalar = json.JSONEncoder(ensure_ascii=self.ensure_ascii,
        allow_nan=self.allow_nan)
    while stack:
      action, value, level = stack.pop()
      if action == 'text':
        yield value
      elif action == 'leave':
        active.remove(id(value))
      elif value is None or isinstance(value, (str, int, float, bool)):
        yield scalar.encode(value)
      else:
        if self.check_circular:
          ident = id(value)
          if ident in active:
            raise ValueError('Circular reference detected')
          active.add(ident)
          stack.append(('leave', value, level))
        if isinstance(value, (list, tuple)):
          yield '['
          newline = '\n' + indent * level if indent is not None and value else ''
          stack.append(('text', newline + ']', level))
          for i in reversed(range(len(value))):
            stack.append(('value', value[i], level + 1))
            if indent is not None:
              stack.append(('text', '\n' + indent * (level + 1), level))
            if i:
              stack.append(('text', self.item_separator, level))
        elif isinstance(value, dict):
          yield '{'
          items = sorted(value.items()) if self.sort_keys else list(value.items())
          entries = []
          for key, part in items:
            if not isinstance(key, str):
              if key is None or isinstance(key, (int, float, bool)):
                key = scalar.encode(key)
              elif self.skipkeys:
                continue
              else:
                raise TypeError('JSON keys must be strings or scalars')
            entries.append((key, part))
          newline = '\n' + indent * level if indent is not None and entries else ''
          stack.append(('text', newline + '}', level))
          for i in reversed(range(len(entries))):
            key, part = entries[i]
            stack.append(('value', part, level + 1))
            stack.append(('text', self.key_separator, level))
            stack.append(('text', scalar.encode(key), level))
            if indent is not None:
              stack.append(('text', '\n' + indent * (level + 1), level))
            if i:
              stack.append(('text', self.item_separator, level))
        else:
          stack.append(('value', self.default(value), level))

  @dispatch.on('obj')
  def default(self, obj):
    return json.JSONEncoder.default(self, obj)

  KEY_MAP = {
      'filename'  : None
    , 'fullname'  : 'name'
    , 'IModule'   : 'IProg'
    , 'IDataType' : 'IType'
    , 'symbolname': 'name'
  }

  VALUE_MAP = {
      'aliases'  : lambda v: list(v)
    , 'functions': lambda v: list(v.values())
    , 'imports'  : lambda v: list(v)
    , 'types'    : lambda v: list(v.values())
  }

  @default.when(types.IObject)
  def default(self, iobj):
    data = collections.OrderedDict()
    clsname = type(iobj).__name__
    data['__class__'] = self.KEY_MAP.get(clsname, clsname)
    for k in getattr(iobj, '_fields_', iobj.__dict__):
      v = getattr(iobj, k)
      if isinstance(iobj, types.IInt) and k == 'value' and not -2 ** 63 <= v < 2 ** 63:
        v = int_text(v)
      vmapper = self.VALUE_MAP.get(k)
      k = self.KEY_MAP.get(k, k)
      if k is not None:
        if vmapper is not None:
          v = vmapper(v)
        data[k] = v
    return data

_encoders = {}

def dumps(icurry, compact=True):
  '''Dump ICurry as JSON.  See :class:`Encoder` for the two forms.'''
  encoder = _encoders.get(compact)
  if encoder is None:
    encoder = _encoders[compact] = get_encoder(compact)
  json = encoder.encode(icurry)
  return ensure_str(json)

def dump(icurry, file, compact=True):
  if isinstance(file, str):
    with open(file, 'w', encoding='utf-8') as ostream:
      ostream.write(dumps(icurry, compact))
  else:
    file.write(dumps(icurry, compact))


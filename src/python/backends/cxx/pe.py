'''Read a PE32+ module's exported bill of materials without loading its DLL.'''
import struct


def record_names(filename):
  with open(filename, 'rb') as stream:
    data = stream.read()

  def unpack(fmt, offset):
    if offset < 0 or offset + struct.calcsize(fmt) > len(data):
      raise ValueError('truncated PE module')
    return struct.unpack_from(fmt, data, offset)

  if data[:2] != b'MZ':
    raise ValueError('not a PE module')
  nt, = unpack('<I', 0x3c)
  if data[nt:nt + 4] != b'PE\0\0':
    raise ValueError('invalid PE signature')
  machine, nsections = unpack('<HH', nt + 4)
  optional_size, = unpack('<H', nt + 20)
  optional = nt + 24
  magic, = unpack('<H', optional)
  if machine != 0x8664 or magic != 0x20b or optional_size < 120:
    raise ValueError('Curry module requires Windows x64 PE32+')
  base, = unpack('<Q', optional + 24)
  header_size, = unpack('<I', optional + 60)
  ndirectories, = unpack('<I', optional + 108)
  exports, export_size = unpack('<II', optional + 112)
  if not ndirectories or not exports:
    raise ValueError('PE module has no exports')
  sections = [unpack('<IIII', optional + optional_size + i * 40 + 8)
              for i in range(nsections)]

  def offset(rva, size):
    if 0 <= rva and rva + size <= min(header_size, len(data)):
      return rva
    for virtual_size, address, raw_size, raw in sections:
      delta = rva - address
      if 0 <= delta and delta + size <= raw_size and raw + delta + size <= len(data):
        return raw + delta
    raise ValueError('PE module address is outside file data')

  def at(fmt, rva):
    return unpack(fmt, offset(rva, struct.calcsize(fmt)))

  def string(rva):
    out = bytearray()
    while True:
      byte, = at('<B', rva + len(out))
      if byte == 0:
        return out.decode('utf-8')
      out.append(byte)

  nfunctions, nnames, functions, names, ordinals = at('<IIIII', exports + 20)
  # Validate the complete arrays before using their counts.
  offset(functions, nfunctions * 4)
  offset(names, nnames * 4)
  offset(ordinals, nnames * 2)
  record = None
  for i in range(nnames):
    name, = at('<I', names + i * 4)
    if string(name) == '_bom_':
      ordinal, = at('<H', ordinals + i * 2)
      if ordinal >= nfunctions:
        raise ValueError('invalid PE export ordinal')
      record, = at('<I', functions + ordinal * 4)
      if exports <= record < exports + export_size:
        raise ValueError('forwarded Curry module record')
      break
  if record is None:
    raise ValueError('PE module has no _bom_ record')
  # bom::Module's header on x64: unsigned, padding, three pointers,
  # unsigned. All its names and import pointers have static initializers.
  version, fullname, filename_ptr, imports, count = at('<I4xQQQI', record)
  if version != 3:
    raise ValueError('unsupported Curry module record version %d' % version)
  if count:
    offset(imports - base, count * 8)
  return string(fullname - base), [
      string(at('<Q', imports - base + i * 8)[0] - base)
      for i in range(count)]

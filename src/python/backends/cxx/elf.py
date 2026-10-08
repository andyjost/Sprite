'''
A reader of the dynamic section of an ELF shared object: the names it
needs (``DT_NEEDED``), its own name (``DT_SONAME``) and its search paths
(``DT_RPATH``, ``DT_RUNPATH``).  It reads what ``readelf -d`` prints for
those tags, without the binutils.

The loader of the C++ backend reads the needed names of an object before it
opens the object: a compiled module names the objects of its imports by
their SONAMEs (see ``toolchain.soname``), and the modules must be loaded
before the dynamic linker looks for the names.  The tests read the SONAME
and the needed names of a compiled module.

The reader finds the dynamic section through the program headers
(``PT_DYNAMIC``), as the dynamic linker does, and the strings through the
loadable segment that maps the string table.  So it reads an object whose
section headers were stripped (``strip --strip-section-headers``), which
the dynamic linker still loads.  It reads the header, the program headers
and the two sections with seeks, not the whole file.

The reader handles the 64-bit format of either byte order, which is what
the C++ compiler writes on the platforms Sprite supports.
'''
import struct

__all__ = ['DynamicSection', 'read_dynamic']

# The tags of the dynamic section that name a string, and the two that
# locate the string table.
DT_NULL    = 0
DT_NEEDED  = 1
DT_STRTAB  = 5
DT_STRSZ   = 10
DT_SONAME  = 14
DT_RPATH   = 15
DT_RUNPATH = 29

# The types of the program headers.
PT_LOAD    = 1
PT_DYNAMIC = 2

# The size of an entry of the dynamic section: a tag and a value.
DYN_ENTRY_SIZE = 16

class DynamicSection(object):
  '''The string entries of the dynamic section of a shared object.'''
  def __init__(self, needed, soname, rpath, runpath):
    self.needed = needed    # the DT_NEEDED names, in order
    self.soname = soname    # the DT_SONAME, or None
    self.rpath = rpath      # the DT_RPATH, or None
    self.runpath = runpath  # the DT_RUNPATH, or None

  def __repr__(self):
    return 'DynamicSection(needed=%r, soname=%r, rpath=%r, runpath=%r)' % (
        self.needed, self.soname, self.rpath, self.runpath
      )

def _read(stream, offset, size, what, filename):
  '''Reads ``size`` bytes at ``offset``; ValueError when the file is short.'''
  stream.seek(offset)
  data = stream.read(size)
  if len(data) != size:
    raise ValueError('%r is truncated: %s ends past the file' % (filename, what))
  return data

def read_dynamic(filename):
  '''
  Reads the dynamic section of the shared object ``filename``.  Returns a
  DynamicSection.

  Raises:
    ValueError: the file is not a 64-bit ELF file, or has no dynamic
      section (a relocatable or a static object), or is truncated.
    OSError: the file cannot be read.
  '''
  with open(filename, 'rb') as stream:
    header = stream.read(64)
    if header[:4] != b'\x7fELF':
      raise ValueError('%r is not an ELF file' % filename)
    if len(header) < 64 or header[4] != 2:
      raise ValueError('%r is not a 64-bit ELF file' % filename)
    if header[5] not in (1, 2):
      raise ValueError('%r has an unknown byte order' % filename)
    order = '<' if header[5] == 1 else '>'
    # The program header table: its offset, the size of an entry, and the
    # number of entries, from the ELF header.
    phoff, = struct.unpack_from(order + 'Q', header, 0x20)
    phentsize, phnum = struct.unpack_from(order + 'HH', header, 0x36)
    if phoff == 0 or phnum == 0:
      raise ValueError('%r has no program headers' % filename)
    table = _read(stream, phoff, phentsize * phnum, 'the program headers', filename)
    loads, dynamic = [], None
    for i in range(phnum):
      # p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz,
      # p_align.
      p_type, _, p_offset, p_vaddr, _, p_filesz, _, _ = struct.unpack_from(
          order + 'IIQQQQQQ', table, i * phentsize
        )
      if p_type == PT_LOAD:
        loads.append((p_vaddr, p_offset, p_filesz))
      elif p_type == PT_DYNAMIC and dynamic is None:
        dynamic = (p_offset, p_filesz)
    if dynamic is None:
      raise ValueError('%r has no dynamic section' % filename)
    entries = []
    data = _read(stream, dynamic[0], dynamic[1], 'the dynamic section', filename)
    for at in range(0, len(data) - DYN_ENTRY_SIZE + 1, DYN_ENTRY_SIZE):
      tag, value = struct.unpack_from(order + 'qQ', data, at)
      if tag == DT_NULL:
        break
      entries.append((tag, value))
    tags = dict(entries)
    if DT_STRTAB not in tags or DT_STRSZ not in tags:
      raise ValueError('%r has no dynamic string table' % filename)
    # DT_STRTAB is a virtual address; the segment that maps it gives the
    # offset in the file.
    strtab_vaddr, strtab_size = tags[DT_STRTAB], tags[DT_STRSZ]
    for p_vaddr, p_offset, p_filesz in loads:
      if p_vaddr <= strtab_vaddr < p_vaddr + p_filesz:
        strtab_offset = p_offset + strtab_vaddr - p_vaddr
        break
    else:
      raise ValueError('%r maps no dynamic string table' % filename)
    strtab = _read(stream, strtab_offset, strtab_size, 'the string table', filename)
  def string(at):
    end = strtab.find(b'\0', at)
    return strtab[at:end if end >= 0 else None].decode('utf-8', 'replace')
  needed, soname, rpath, runpath = [], None, None, None
  for tag, value in entries:
    if tag == DT_NEEDED:
      needed.append(string(value))
    elif tag == DT_SONAME:
      soname = string(value)
    elif tag == DT_RPATH:
      rpath = string(value)
    elif tag == DT_RUNPATH:
      runpath = string(value)
  return DynamicSection(needed, soname, rpath, runpath)

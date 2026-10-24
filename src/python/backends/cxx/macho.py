'''
A reader of the load commands of a Mach-O shared library (macOS): the
libraries it loads (``LC_LOAD_DYLIB`` and its weak, re-export and upward
forms), its own install name (``LC_ID_DYLIB``) and its run paths
(``LC_RPATH``).  It reads what ``otool -L`` and ``otool -l`` print for those
commands, without the Xcode tools, and returns the same ``DynamicSection``
as the ELF reader (``elf.read_dynamic``): the install name stands as the
SONAME, the loaded libraries as the needed names, and the run paths,
joined by colons, as the rpath.

The loader of the C++ backend reads the needed names of an object before it
opens it, and the toolchain reads the imports of an object to judge its
staleness (``loader.needed_modules``); on macOS the compiled modules are
Mach-O files, named with ``-install_name`` by the same scheme as the SONAME
of an ELF object (``toolchain.soname``).

The reader handles the 64-bit format of either byte order, and refuses a
32-bit or a universal (fat) file: the toolchain writes thin 64-bit objects.
It reads the header and the load commands with two reads, not the whole
file.
'''
import struct
from .elf import DynamicSection

__all__ = ['read_dynamic', 'MAGICS']

# The magic of a 64-bit Mach-O file, as the first four bytes read in the
# byte order of the file: little-endian (every current Apple platform) and
# big-endian, each with the struct format of its order.
MAGICS = {b'\xcf\xfa\xed\xfe': '<', b'\xfe\xed\xfa\xcf': '>'}
MAGIC_32 = {b'\xce\xfa\xed\xfe', b'\xfe\xed\xfa\xce'}
MAGIC_FAT = {b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca'}

HEADER_SIZE = 32   # mach_header_64: eight 32-bit fields.
LC_REQ_DYLD = 0x80000000
LC_ID_DYLIB = 0xd
LC_LOAD_DYLIB = 0xc
LC_LOAD_WEAK_DYLIB = 0x18 | LC_REQ_DYLD
LC_REEXPORT_DYLIB = 0x1f | LC_REQ_DYLD
LC_LOAD_UPWARD_DYLIB = 0x23 | LC_REQ_DYLD
LC_RPATH = 0x1c | LC_REQ_DYLD
NEEDED_COMMANDS = frozenset([
    LC_LOAD_DYLIB, LC_LOAD_WEAK_DYLIB, LC_REEXPORT_DYLIB, LC_LOAD_UPWARD_DYLIB
  ])

def _lc_str(command, order, offset_field, filename):
  '''
  The string of a load command: the ``lc_str`` at ``offset_field`` of the
  command names the offset of a NUL-terminated string from the start of
  the command, inside its size.
  '''
  if len(command) < offset_field + 4:
    raise ValueError('%r has a load command that is too short' % filename)
  offset, = struct.unpack_from(order + 'I', command, offset_field)
  if offset >= len(command):
    raise ValueError('%r has a load command whose string lies past it' % filename)
  text = command[offset:]
  end = text.find(b'\0')
  return (text if end < 0 else text[:end]).decode('utf-8', 'replace')

def read_dynamic(filename):
  '''
  Reads the load commands of the Mach-O shared library ``filename``.
  Returns a DynamicSection: the loaded libraries as ``needed``, the
  install name as ``soname`` (None without one), the run paths joined by
  colons as ``rpath`` (None without one), and ``runpath`` None.

  Raises:
    ValueError: the file is not a thin 64-bit Mach-O file, or its load
    commands are malformed.
  '''
  with open(filename, 'rb') as stream:
    header = stream.read(HEADER_SIZE)
    magic = header[:4]
    if magic in MAGIC_FAT:
      raise ValueError('%r is a universal binary; a thin 64-bit Mach-O file is needed' % filename)
    if magic in MAGIC_32:
      raise ValueError('%r is not a 64-bit Mach-O file' % filename)
    if magic not in MAGICS:
      raise ValueError('%r is not a Mach-O file' % filename)
    order = MAGICS[magic]
    if len(header) != HEADER_SIZE:
      raise ValueError('%r is truncated: the header ends past the file' % filename)
    ncmds, sizeofcmds = struct.unpack_from(order + 'II', header, 16)
    commands = stream.read(sizeofcmds)
    if len(commands) != sizeofcmds:
      raise ValueError('%r is truncated: the load commands end past the file' % filename)
  needed, soname, rpaths = [], None, []
  position = 0
  for _ in range(ncmds):
    if position + 8 > len(commands):
      raise ValueError('%r has fewer load commands than its header says' % filename)
    cmd, cmdsize = struct.unpack_from(order + 'II', commands, position)
    if cmdsize < 8 or position + cmdsize > len(commands):
      raise ValueError('%r has a load command of a bad size' % filename)
    command = commands[position:position + cmdsize]
    if cmd == LC_ID_DYLIB:
      soname = _lc_str(command, order, 8, filename)
    elif cmd in NEEDED_COMMANDS:
      needed.append(_lc_str(command, order, 8, filename))
    elif cmd == LC_RPATH:
      rpaths.append(_lc_str(command, order, 8, filename))
    position += cmdsize
  return DynamicSection(needed, soname, ':'.join(rpaths) or None, None)

'''The reader of the load commands of a Mach-O object, on a synthetic file.'''
import cytest # from ./lib; must be first
from curry.backends.cxx import elf, loader, macho
import os, struct, tempfile, unittest

def lc_str_command(cmd, text, order='<', extra=12):
  '''
  A load command with one lc_str: the string offset is 8 plus ``extra``
  bytes of the other fields (a dylib command has 12), padded to 8 bytes.
  '''
  payload = text.encode('utf-8') + b'\0'
  size = 8 + extra + len(payload)
  size += (-size) % 8
  body = struct.pack(order + 'II', cmd, size) + struct.pack(order + 'I', 8 + extra)
  body += b'\0' * (extra - 4) + payload
  return body + b'\0' * (size - len(body))

def macho_file(commands, order='<', magic=None):
  '''A thin 64-bit Mach-O file of the given load commands and nothing else.'''
  body = b''.join(commands)
  magic = magic or (b'\xcf\xfa\xed\xfe' if order == '<' else b'\xfe\xed\xfa\xcf')
  header = magic + struct.pack(
      order + 'IIIIIII', 0x0100000c, 0, 6, len(commands), len(body), 0, 0
    )
  return header + body

class TestMachOReader(cytest.TestCase):

  def write(self, data):
    fd, path = tempfile.mkstemp(suffix='.so')
    with os.fdopen(fd, 'wb') as stream:
      stream.write(data)
    self.addCleanup(os.unlink, path)
    return path

  def test_names_and_paths(self):
    '''The install name, the loaded libraries in order, and the run paths.'''
    for order in '<', '>':
      with self.subTest(order=order):
        path = self.write(macho_file([
            lc_str_command(macho.LC_ID_DYLIB, 'sprite-Data.List.so.14', order)
          , lc_str_command(macho.LC_LOAD_DYLIB, 'sprite-Prelude.so.14', order)
          , lc_str_command(macho.LC_LOAD_WEAK_DYLIB, 'sprite-Data.Maybe.so.14', order)
          , lc_str_command(macho.LC_LOAD_DYLIB, '@rpath/libcurryrt.dylib', order)
          , lc_str_command(macho.LC_LOAD_DYLIB, '/usr/lib/libSystem.B.dylib', order)
          , lc_str_command(macho.LC_RPATH, '@loader_path/../lib', order, extra=4)
          , lc_str_command(macho.LC_RPATH, '/opt/sprite/lib', order, extra=4)
          ], order))
        dynamic = macho.read_dynamic(path)
        self.assertIsInstance(dynamic, elf.DynamicSection)
        self.assertEqual(dynamic.soname, 'sprite-Data.List.so.14')
        self.assertEqual(dynamic.needed, [
            'sprite-Prelude.so.14', 'sprite-Data.Maybe.so.14'
          , '@rpath/libcurryrt.dylib', '/usr/lib/libSystem.B.dylib'
          ])
        self.assertEqual(dynamic.rpath, '@loader_path/../lib:/opt/sprite/lib')
        self.assertIsNone(dynamic.runpath)
        # The loader reads the module names through the dispatch by format.
        self.assertEqual(loader.read_dynamic(path).soname, dynamic.soname)
        self.assertEqual(loader.needed_modules(path), ['Prelude', 'Data.Maybe'])

  def test_without_an_install_name(self):
    path = self.write(macho_file([lc_str_command(macho.LC_LOAD_DYLIB, 'a.dylib')]))
    dynamic = macho.read_dynamic(path)
    self.assertIsNone(dynamic.soname)
    self.assertIsNone(dynamic.rpath)
    self.assertEqual(dynamic.needed, ['a.dylib'])

  def test_refusals(self):
    '''A 32-bit file, a universal binary, another format, and truncation.'''
    for data, message in [
        (macho_file([], magic=b'\xce\xfa\xed\xfe'), 'not a 64-bit Mach-O')
      , (b'\xca\xfe\xba\xbe' + b'\0' * 40, 'universal binary')
      , (b'\x7fELF' + b'\0' * 40, 'not a Mach-O file')
      , (macho_file([lc_str_command(macho.LC_LOAD_DYLIB, 'a.dylib')])[:-10], 'truncated')
      ]:
      with self.subTest(message=message):
        with self.assertRaisesRegex(ValueError, message):
          macho.read_dynamic(self.write(data))
    with self.assertRaisesRegex(ValueError, 'neither an ELF nor a Mach-O'):
      loader.read_dynamic(self.write(b'not an object at all'))

  def test_the_dispatch_reads_elf(self):
    '''The runtime library of this installation, when it is an ELF file.'''
    from curry import config
    lib = config.curryrt_lib()
    with open(lib, 'rb') as stream:
      if stream.read(4) != b'\x7fELF':
        raise unittest.SkipTest('the runtime library is not an ELF file here')
    self.assertEqual(loader.read_dynamic(lib).soname, elf.read_dynamic(lib).soname)

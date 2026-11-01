'''Windows compile commands and the DLL/import/compiled-step contract.'''
import cytest  # from ./lib; must be first
import curry
from curry import config
from curry.backends.cxx import toolchain
from curry.objects.handle import getHandle
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


class TestWindowsTestLibrary(cytest.TestCase):
  def test_tty_import_without_posix_c_streams(self):
    import ctypes
    import runpy
    from cytest import tty
    with mock.patch.object(os, 'name', 'nt'), \
         mock.patch.object(ctypes, 'CDLL', side_effect=AssertionError('POSIX libc')):
      namespace = runpy.run_path(tty.__file__)
    for name, args in [('close_stdin', ()), ('close_stdout', ()),
                       ('redirect_stdin', (None,)), ('redirect_stdout', (None,))]:
      with self.subTest(name=name), self.assertRaisesRegex(unittest.SkipTest, 'POSIX'):
        with namespace[name](*args):
          self.fail('unsupported C stream operation ran')

  def test_windows_limit_prefix_ignores_timeout_exe(self):
    with mock.patch.object(sys, 'platform', 'win32'), \
         mock.patch.object(shutil, 'which', return_value='timeout.exe'):
      self.assertEqual(cytest.limit_prefix(1024, 5), [])

  def test_alarm_timeout_skips_without_sigalrm(self):
    import types
    with mock.patch.object(cytest, 'signal', types.SimpleNamespace()):
      with self.assertRaisesRegex(unittest.SkipTest, 'SIGALRM'):
        with cytest.timeout(1):
          self.fail('unsupported alarm ran')


class TestWindowsCommand(cytest.TestCase):
  def test_clang_cl_links_only_the_runtime(self):
    step = toolchain.Cpp2So(cytest.raw.interp())
    with mock.patch.object(toolchain, 'IS_WINDOWS', True), \
         mock.patch.object(config, 'cxx_tool', return_value='clang-cl'), \
         mock.patch.object(step, '_pchflags', side_effect=AssertionError('PCH')), \
         mock.patch.object(step, '_dependencies', side_effect=AssertionError('module link')):
      command = list(step._compileCommand('Module.cpp', 'Module.dll'))
      self.assertEqual(command[:2], ['clang-cl', '/LD'])
      for flag in ['/std:c++17', '/EHsc', '/MD', '/O2', '/DNDEBUG',
                   '/clang:-fno-strict-aliasing', '/link', '/OUT:Module.dll']:
        self.assertIn(flag, command)
      self.assertEqual(command[-1], config.installed_path('lib', 'libcurryrt.lib'))
      self.assertFalse(any('soname' in flag or 'entry' in flag for flag in command))

  def test_debug_uses_debug_crt_and_private_pdb(self):
    step = toolchain.Cpp2So(cytest.raw.interp())
    with mock.patch.object(toolchain, 'IS_WINDOWS', True), \
         mock.patch.object(type(step), 'flavor', new_callable=mock.PropertyMock, return_value='debug'), \
         mock.patch.object(config, 'cxx_tool', return_value='clang-cl'):
      command = list(step._compileCommand('Module.cpp', 'Module.dll'))
      for flag in ['/MDd', '/D_DEBUG', '/Zi', '/FdModule.dll.pdb']:
        self.assertIn(flag, command)
      self.assertNotIn('/MD', command)

  def test_saved_program_is_linked_as_an_executable(self):
    from curry.interpreter import session
    with tempfile.TemporaryDirectory() as work:
      output = os.path.join(work, 'saved.exe')
      captured = []
      def compile(command):
        captured.extend(command)
        text = Path(work, 'launcher.cpp').read_text()
        self.assertIn('int wmain(', text)
        self.assertIn('_wspawnvp(_P_WAIT', text)
        self.assertIn('remove_all(directory', text)
        self.assertNotIn('TemporaryDirectory(', text)
      program = "#!/python\nimport base64, os, tempfile\nwith tempfile.TemporaryDirectory(prefix='sprite-program-') as work:\n  pass\n"
      with mock.patch.object(toolchain, 'IS_WINDOWS', True), \
           mock.patch.object(config, 'cxx_tool', return_value='clang-cl'), \
           mock.patch('curry.toolchain._system.pexec', side_effect=compile), \
           mock.patch.object(shutil, 'copyfile') as copy:
        session._save_windows_program(cytest.raw.interp(), output, program, work)
      self.assertNotIn('/LD', captured)
      self.assertFalse(any(flag.startswith('/IMPLIB:') for flag in captured))
      self.assertIn('/OUT:' + output, captured)
      self.assertEqual(captured[-1], config.installed_path('lib', 'libcurryrt.lib'))
      copy.assert_called_once_with(config.installed_path('lib', 'libcurryrt.dll'),
                                   os.path.join(work, 'libcurryrt.dll'))

  def test_windows_flags_change_the_abi_digest(self):
    with mock.patch.object(toolchain, 'IS_WINDOWS', True), \
         mock.patch.object(toolchain, 'runtime_digest', return_value='headers'):
      before = toolchain.object_digest()
      with mock.patch.object(toolchain, 'MSVC_FLAGS', toolchain.MSVC_FLAGS + ['/DABI_TEST']):
        self.assertNotEqual(toolchain.object_digest(), before)


class TestTableExports(cytest.TestCase):
  @unittest.skipUnless(sys.platform == 'win32', 'Windows runtime exports')
  def test_runtime_exports_builtin_datatypes(self):
    exports = subprocess.check_output([
        'dumpbin', '/nologo', '/exports',
        config.installed_path('lib', 'libcurryrt.dll')], text=True)
    print(exports)
    names = set(exports.split())
    for symbol in ['CyD7Prelude3Int', 'CyD7Prelude4Bool', 'CyD7Prelude4Char',
                   'CyD7Prelude5Float', 'CyD7Prelude2IO', 'CyD7Prelude4_Y_y',
                   'CyD7Prelude4_K_k', 'CyD7Prelude6_Y_m_y']:
      with self.subTest(symbol=symbol):
        self.assertIn(symbol, names)

  def test_first_declarations_of_defined_tables_are_exported(self):
    from curry.backends.cxx import compiler
    from curry.interpreter.loadsave import compilable_icurry
    for name in ['CxxBom', 'Prelude']:
      with self.subTest(module=name):
        # Direct unittest runs do not inherit run_tests' fixture CURRYPATH.
        source = Path(__file__).parent / 'data' / 'curry' / 'CxxBom.curry'
        module = curry.import_(str(source) if name == 'CxxBom' else name)
        interp = cytest.raw.interp()
        target = compiler.compile(interp, compilable_icurry(
            interp, module, getHandle(module).icurry))
        from curry.backends.generic import renderer
        text = '\n'.join(renderer.CXX_RENDERER.renderLines(target[section])
                         for section in target.SECTIONS)
        self.assertIn('extern SPRITE_MODULE_EXPORT bom::Module const _bom_;',
                      target['.moduledef'])
        for links, definitions in [('.infotabs.link', '.infotabs'),
                                    ('.datatypes.link', '.datatypes')]:
          defined = set(re.findall(
              r'SPRITE_MODULE_EXPORT (?:InfoTable|DataType) const (Cy\w+)\s*\{',
              '\n'.join(target[definitions])))
          self.assertTrue(defined)
          declared = set()
          for line in target[links]:
            match = re.match(r'extern (.*?)(?:InfoTable|DataType) const (Cy\w+);', line)
            if match:
              attribute, symbol = match.groups()
              declared.add(symbol)
              self.assertEqual(attribute == 'SPRITE_MODULE_EXPORT ', symbol in defined)
              if symbol not in defined:
                self.assertIn(attribute, ['', 'CURRYRT_DATA '])
                if not attribute:
                  # Another module's table must never become a link-time
                  # dependency, even in constructor arrays or BOM records.
                  self.assertNotRegex(text, r'&\s*' + re.escape(symbol) + r'\b')
          self.assertTrue(defined <= declared)
          self.assertTrue(declared - defined)


class TestWindowsPublication(cytest.TestCase):
  def test_loaded_canonical_product_can_be_republished(self):
    with mock.patch.dict(os.environ, SPRITE_TEST_WINDOWS_PUBLICATION='1'), \
         tempfile.TemporaryDirectory(prefix='sprite-publication-',
                                     ignore_cleanup_errors=True) as work:
      source = Path(work) / 'WindowsPublication.curry'
      source.write_text('module WindowsPublication where\nanswer :: Int\nanswer = 42\n')
      curry.reset(interpret='off', jit='off')
      module = curry.import_(str(source))
      self.assertEqual(curry.eval(module.answer).one(), 42)
      product = Path(getHandle(module).sofilename)
      copies = list(product.parent.glob(product.name + '.old-*'))
      self.assertFalse(copies, 'loading must not write beside the canonical file')
      toolchain.Cpp2So(cytest.raw.interp())(str(product.with_suffix('.cpp')), curry.path, is_sourcefile=True)
      copies = list(product.parent.glob(product.name + '.old-*'))
      self.assertTrue(copies)
      # A second process maps this generation and then publishes again.
      # Its retired generation becomes collectable only after it exits.
      script = """
import curry, sys
from curry.backends.cxx import toolchain
from curry.toolchain import _filenames
curry.reset(interpret='off', jit='off')
module = curry.import_(sys.argv[1])
cpp = _filenames.replacesuffix(sys.argv[1], '.cpp')
step = toolchain.Cpp2So(curry._interpreter_)
step(cpp, curry.path, is_sourcefile=True)
assert curry.eval(module.answer).one() == 42
"""
      child = subprocess.run([sys.executable, '-c', script, str(source)],
                             capture_output=True, text=True, timeout=120)
      self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
      stale = [p for p in product.parent.glob(product.name + '.old-*')
               if p not in copies]
      self.assertTrue(stale, 'the child must leave its retired generation')
      # Publication cleans dead owners without removing live readers.
      cpp = str(product.with_suffix('.cpp'))
      toolchain.Cpp2So(cytest.raw.interp())(cpp, curry.path, is_sourcefile=True)
      self.assertTrue(all(not path.exists() for path in stale))
      self.assertTrue(all(path.exists() for path in copies))
      self.assertEqual(curry.eval(module.answer).one(), 42)

  @unittest.skipIf(sys.platform == 'win32', 'POSIX directory permission regression')
  def test_read_only_publication_leaves_directory_untouched(self):
    if os.geteuid() == 0:
      self.skipTest('root can write a read-only directory')
    from curry.backends.cxx import curryrtbindings
    with tempfile.TemporaryDirectory() as work, \
         mock.patch.dict(os.environ, SPRITE_TEST_WINDOWS_PUBLICATION='1'):
      directory = Path(work) / 'products'
      directory.mkdir()
      canonical = directory / 'Module.so'
      canonical.write_bytes(b'current')
      pending = Path(work) / 'pending.so'
      pending.write_bytes(b'new')
      directory.chmod(0o555)
      try:
        with self.assertRaisesRegex(RuntimeError, 'cannot publish object'):
          curryrtbindings.publish_object(str(pending), str(canonical))
        self.assertEqual(list(directory.iterdir()), [canonical])
        self.assertEqual(canonical.read_bytes(), b'current')
        self.assertEqual(pending.read_bytes(), b'new')
      finally:
        directory.chmod(0o755)

  def test_read_only_import_does_not_write_products(self):
    with tempfile.TemporaryDirectory(prefix='sprite-read-only-',
                                     ignore_cleanup_errors=True) as work:
      source = Path(work) / 'ReadOnlyObject.curry'
      source.write_text('module ReadOnlyObject where\nanswer :: Int\nanswer = 42\n')
      curry.reset(interpret='off', jit='off')
      module = curry.import_(str(source))
      product = Path(getHandle(module).sofilename)
      directory = product.parent
      before = {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}
      mode = directory.stat().st_mode
      directory.chmod(0o555)
      try:
        script = "import curry, sys; curry.reset(interpret='new', jit='off'); m = curry.import_(sys.argv[1]); assert curry.eval(m.answer).one() == 42"
        child = subprocess.run([sys.executable, '-c', script, str(source)],
                               capture_output=True, text=True, timeout=120)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
        after = {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}
        self.assertEqual(after, before)
      finally:
        directory.chmod(mode)


class TestPERecord(cytest.TestCase):
  def image(self):
    import struct
    data = bytearray(0x800)
    base = 0x180000000
    def put(fmt, offset, *values):
      struct.pack_into(fmt, data, offset, *values)
    def address(rva):
      return 0x200 + rva - 0x1000
    def text(rva, value):
      start = address(rva)
      data[start:start + len(value) + 1] = value.encode('ascii') + b'\0'
    data[:2] = b'MZ'
    put('<I', 0x3c, 0x80)
    data[0x80:0x84] = b'PE\0\0'
    put('<HH', 0x84, 0x8664, 1)
    put('<H', 0x94, 0xf0)
    put('<H', 0x98, 0x20b)
    put('<Q', 0x98 + 24, base)
    put('<I', 0x98 + 60, 0x200)
    put('<I', 0x98 + 108, 16)
    put('<II', 0x98 + 112, 0x1000, 0x80)
    put('<IIII', 0x98 + 0xf0 + 8, 0x600, 0x1000, 0x600, 0x200)
    put('<IIIII', address(0x1000) + 20, 1, 1, 0x1040, 0x1044, 0x1048)
    put('<I', address(0x1040), 0x1100)
    put('<I', address(0x1044), 0x1050)
    put('<H', address(0x1048), 0)
    text(0x1050, '_bom_')
    put('<I4xQQQI', address(0x1100), 2, base + 0x1180, 0, base + 0x11c0, 2)
    text(0x1180, 'Test.Module')
    put('<QQ', address(0x11c0), base + 0x1200, base + 0x1210)
    text(0x1200, 'Prelude')
    text(0x1210, 'Data.Maybe')
    return data

  def read(self, data):
    from curry.backends.cxx.pe import record_names
    with tempfile.TemporaryDirectory(prefix='sprite-pe-record-') as work:
      path = Path(work) / 'Module.dll'
      path.write_bytes(data)
      return record_names(path)

  def test_record_names_without_loading_the_dll(self):
    self.assertEqual(self.read(self.image()), ('Test.Module', ['Prelude', 'Data.Maybe']))

  def test_loader_dispatches_by_object_magic(self):
    from curry.backends.cxx import loader
    with tempfile.TemporaryDirectory(prefix='sprite-pe-dispatch-') as work:
      path = Path(work) / 'Module.dll'
      path.write_bytes(self.image())
      with mock.patch.object(loader.sys, 'platform', 'linux'):
        self.assertEqual(loader._dynamic_names(path),
                         ('Test.Module', ['Prelude', 'Data.Maybe']))

  def test_invalid_record_is_refused(self):
    import struct
    data = self.image()
    struct.pack_into('<I', data, 0x300, 99)
    with self.assertRaisesRegex(ValueError, 'record version'):
      self.read(data)
    with self.assertRaises(ValueError):
      self.read(self.image()[:0x210])


@unittest.skipUnless(sys.platform == 'win32', 'Windows DLL integration')
class TestWindowsDLL(cytest.TestCase):
  def setUp(self):
    super().setUp()
    self.work = Path(tempfile.mkdtemp(prefix='sprite-windows-aot-'))
    # Loaded DLLs remain mapped for the lifetime of the process.
    self.addCleanup(shutil.rmtree, self.work, True)
    curry.reset(interpret='new', jit='off')
    curry.path.insert(0, str(self.work))

  def make(self, source):
    start = time.perf_counter()
    subprocess.run([sys.executable, '-m', 'curry.tools.make', '--so', str(source)],
                   check=True, env=dict(os.environ, SPRITE_LOG_LEVEL='INFO'))
    print('%s sprite-make: %.3f seconds' % (source.stem, time.perf_counter() - start))
    return source.parent / '.curry' / config.intermediate_subdir() / (source.stem + '.dll')

  def test_module_and_compiled_import(self):
    source = self.work / 'CxxBom.curry'
    shutil.copy(Path(__file__).parent / 'data/curry/CxxBom.curry', source)
    product = self.make(source)
    exports = subprocess.check_output(['dumpbin', '/nologo', '/exports', str(product)], text=True)
    print(exports)
    for symbol in ['_bom_', '_sprite_init_', 'CyI', 'CyD', 'CyF']:
      self.assertIn(symbol, exports)
    module = curry.load(product)
    self.assertIsNotNone(getHandle(module).icurry.metadata.get('cxx.shlib'))
    from curry.backends.cxx import curryrtbindings as rt
    self.assertFalse(rt.icurry_is_interpreted(module.main.info))
    self.assertEqual(curry.eval(module.main).one(), 9)
    importer = self.work / 'WindowsImport.curry'
    importer.write_text('module WindowsImport where\nimport CxxBom\nanswer :: Int\nanswer = plus 20 22\n')
    product = self.make(importer)
    from curry.backends.cxx.loader import _dynamic_names
    name, imports = _dynamic_names(str(product))
    self.assertEqual(name, 'WindowsImport')
    self.assertIn('CxxBom', imports)
    module = curry.load(product)
    self.assertIsNotNone(getHandle(module).icurry.metadata.get('cxx.shlib'))
    self.assertEqual(curry.eval(module.answer).one(), 42)

  def test_eager_cxx(self):
    source = self.work / 'WindowsEager.curry'
    source.write_text('module WindowsEager where\ndouble :: Int -> Int\ndouble x = x + x\nanswer :: Int\nanswer = double 21\n')
    curry.reset(interpret='new', jit='eager', jit_backend='cxx')
    curry.path.insert(0, str(self.work))
    module = curry.import_(str(source))
    from curry.backends.cxx import curryrtbindings as rt
    self.assertFalse(rt.icurry_is_interpreted(module.answer.info))
    self.assertIsNotNone(getHandle(module).icurry.metadata.get('cxx.shlib'))
    self.assertEqual(curry.eval(module.answer).one(), 42)


@unittest.skipUnless(sys.platform == 'win32', 'Windows process locks')
class TestWindowsLock(cytest.TestCase):
  def test_another_process_waits_for_the_writer(self):
    from curry.toolchain import _productlock
    import threading
    with tempfile.TemporaryDirectory(prefix='sprite-windows-lock-') as work:
      source = os.path.join(work, 'Locked.curry')
      code = """
import sys
from curry.toolchain import _productlock
with _productlock.locked(sys.argv[1]):
  print('held', flush=True)
  sys.stdin.readline()
"""
      child = subprocess.Popen([sys.executable, '-c', code, source],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
      acquired = threading.Event()
      result = []
      def take():
        with _productlock.locked(source) as waited:
          result.append(waited)
          acquired.set()
      thread = threading.Thread(target=take, daemon=True)
      try:
        self.assertEqual(child.stdout.readline().strip(), 'held')
        thread.start()
        self.assertFalse(acquired.wait(0.2))
        child.stdin.write('release\n')
        child.stdin.flush()
        self.assertTrue(acquired.wait(30))
        thread.join(30)
        self.assertEqual(result, [True])
        self.assertEqual(child.wait(30), 0)
      finally:
        if child.poll() is None:
          child.kill()
        child.wait()
        child.stdin.close()
        child.stdout.close()


if __name__ == '__main__':
  unittest.main()

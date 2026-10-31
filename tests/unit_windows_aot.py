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

  def test_windows_flags_change_the_abi_digest(self):
    with mock.patch.object(toolchain, 'IS_WINDOWS', True), \
         mock.patch.object(toolchain, 'runtime_digest', return_value='headers'):
      before = toolchain.object_digest()
      with mock.patch.object(toolchain, 'MSVC_FLAGS', toolchain.MSVC_FLAGS + ['/DABI_TEST']):
        self.assertNotEqual(toolchain.object_digest(), before)


class TestTableExports(cytest.TestCase):
  def test_first_declarations_of_defined_tables_are_exported(self):
    from curry.backends.cxx import compiler
    from curry.interpreter.loadsave import compilable_icurry
    for name in ['CxxBom', 'Prelude']:
      with self.subTest(module=name):
        module = curry.import_(name)
        interp = cytest.raw.interp()
        target = compiler.compile(interp, compilable_icurry(
            interp, module, getHandle(module).icurry))
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
          self.assertTrue(defined <= declared)
          self.assertTrue(declared - defined)


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

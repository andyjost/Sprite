'''The native module image and its content receipts.'''
import cytest # from ./lib; must be first
import curry
from curry import inspect
from curry.backends.cxx import image, curryrtbindings as curryrt
from curry.objects.handle import getHandle
from unittest import mock
import os
import json
import subprocess
import sys
import struct
import tempfile
import zlib


class TestImage(cytest.TestCase):
  def setUp(self):
    curry.reset(backend='cxx', interpret='all', jit='off')

  def test_prelude(self):
    module = curry.import_('Prelude')
    path = image.filename(getHandle(module).icurry.filename)
    self.assertEqual(image.read(path)['name'], 'Prelude')
    curry.reset(backend='cxx', interpret='all', jit='off')
    with mock.patch('curry.toolchain._loadcurry.loadjson',
        side_effect=AssertionError('image load read JSON')):
      module = curry.import_('Prelude')
    self.assertEqual(curry.eval(getattr(module, 'not')(True)).one(), False)
    self.assertIsNotNone(curryrt.icurry_bytecode(curry.symbol('Prelude.map').info))

  def test_roundtrip_stale_corrupt_and_version(self):
    with tempfile.TemporaryDirectory() as directory:
      source = os.path.join(directory, 'ImageRoundTrip.curry')
      with open(source, 'w') as stream:
        stream.write('module ImageRoundTrip where\ndata T = A | B Int\n'
            'answer :: Int\nanswer = 42\n')
      module = curry.import_(source)
      path = image.filename(source)
      self.assertEqual(curry.eval(module.answer).one(), 42)
      for corruption in ('body', 'header', 'version', 'source'):
        curry.reset(backend='cxx', interpret='all', jit='off')
        with open(path, 'rb') as stream:
          data = bytearray(stream.read())
        if corruption == 'body':
          data[-1] ^= 1
        elif corruption == 'header':
          size = struct.unpack_from('<I', data, 12)[0]
          data.insert(image.PREFIX.size, ord(' '))
          struct.pack_into('<I', data, 12, size + 1)
        elif corruption == 'version':
          struct.pack_into('<I', data, 8, image.VERSION + 1)
        else:
          with open(source, 'a') as stream:
            stream.write('\n-- edited source\n')
        if corruption != 'source':
          with open(path, 'wb') as stream:
            stream.write(data)
        module = curry.import_(source)
        self.assertEqual(curry.eval(module.answer).one(), 42)
        self.assertEqual(image.read(path)['source'], image.digest(source))
      curry.reset(backend='cxx', interpret='all', jit='off')
      with mock.patch('curry.toolchain._loadcurry.loadjson',
          side_effect=AssertionError('image load read JSON')):
        module = curry.import_(source)
      self.assertEqual([x.name for x in getattr(module, '.types')['T'].constructors],
          ['A', 'B'])

  def test_import_digest_budget_and_no_json(self):
    with tempfile.TemporaryDirectory() as directory:
      dep = os.path.join(directory, 'ImageDependency.curry')
      source = os.path.join(directory, 'ImageImporter.curry')
      with open(dep, 'w') as stream:
        stream.write('module ImageDependency where\nf :: Int\nf = 41\n')
      with open(source, 'w') as stream:
        stream.write('module ImageImporter where\nimport ImageDependency\n'
            'answer :: Int\nanswer = f + 1\n')
      module = curry.import_(source)
      path = image.filename(source)
      first = image.digest(path)
      self.assertEqual(curry.eval(module.answer).one(), 42)
      with open(dep, 'w') as stream:
        stream.write('module ImageDependency where\nf :: Int\nf = 42\n')
      curry.reset(backend='cxx', interpret='all', jit='off')
      module = curry.import_(source)
      self.assertEqual(curry.eval(module.answer).one(), 43)
      self.assertNotEqual(image.digest(path), first)
      curry.reset(backend='cxx', interpret='all', jit='off', inline_budget=0)
      module = curry.import_(source)
      self.assertNotEqual(image.read(path)['budget'], 0)
      self.assertEqual(image.read(image._path(curry._interpreter_, source))['budget'], 0)
      self.assertEqual(curry.eval(module.answer).one(), 43)
      from curry.toolchain import _filenames
      for product in _filenames.jsonfilenames(source):
        if os.path.exists(product):
          os.unlink(product)
      curry.reset(backend='cxx', interpret='all', jit='off', inline_budget=0)
      with mock.patch('curry.toolchain._loadcurry.loadjson',
          side_effect=AssertionError('image load read JSON')):
        module = curry.import_(source)
      self.assertEqual(curry.eval(module.answer).one(), 43)

  def test_readonly_uses_json(self):
    from curry.toolchain import _loadcurry
    prelude = curry.import_('Prelude')
    source = getHandle(prelude).icurry.filename
    product_dir = os.path.dirname(image.filename(source))
    access = os.access
    for missing in (False, True):
      with mock.patch.object(os, 'access', side_effect=lambda path, mode:
          False if os.path.realpath(path) == os.path.realpath(product_dir) else access(path, mode)), \
          mock.patch.object(image, 'load', side_effect=AssertionError('image write')), \
          mock.patch.object(_loadcurry, 'loadjson', wraps=_loadcurry.loadjson) as loader:
        with mock.patch.object(image, 'current', return_value=None) if missing else \
            mock.patch.object(image, 'current', wraps=image.current):
          curry.reset(backend='cxx', interpret='all', jit='off')
          module = curry.import_('Prelude')
      self.assertTrue(loader.called)
      self.assertEqual(curry.eval(getattr(module, 'not')(True)).one(), False)

  def test_readonly_missing_image(self):
    with tempfile.TemporaryDirectory() as directory:
      source = os.path.join(directory, 'ImageReadonly.curry')
      with open(source, 'w') as stream:
        stream.write('module ImageReadonly where\nanswer :: Int\nanswer = 42\n')
      curry.import_(source)
      path = image.filename(source)
      os.unlink(path)
      curry.reset(backend='cxx', interpret='all', jit='off')
      access = os.access
      with mock.patch.object(os, 'access', side_effect=lambda name, mode:
          False if name == os.path.dirname(path) else access(name, mode)), \
          mock.patch.object(image, 'load', side_effect=AssertionError('image write')):
        module = curry.import_(source)
      self.assertEqual(curry.eval(module.answer).one(), 42)
      self.assertFalse(os.path.exists(path))

  def test_module_without_file_has_no_image(self):
    from curry import icurry
    module = curry.compile('answer :: Int\nanswer = 42\n')
    raw = getHandle(module).icurry
    with mock.patch.object(raw, 'filename', None), \
        mock.patch.object(module, '.source_mtime', None):
      self.assertIsNone(image.filename(raw.filename))
      self.assertIsNone(image.write(curry._interpreter_, raw))
      self.assertEqual(image._import_images(curry._interpreter_, [raw.fullname], None),
          {raw.fullname: None})
      importer = icurry.IModule('ImageNoFileImporter', [raw.fullname], {}, {})
      image.optimize(curry._interpreter_, importer)

  def test_vanished_import(self):
    with tempfile.TemporaryDirectory() as directory:
      helper = os.path.join(directory, 'ImageVanishedHelper.curry')
      source = os.path.join(directory, 'ImageVanished.curry')
      with open(helper, 'w') as stream:
        stream.write('module ImageVanishedHelper where\nf :: Int\nf = 1\n')
      with open(source, 'w') as stream:
        stream.write('module ImageVanished where\nimport ImageVanishedHelper\n'
            'answer :: Int\nanswer = f\n')
      curry.import_(source)
      os.unlink(helper)
      with open(source, 'w') as stream:
        stream.write('module ImageVanished where\nanswer :: Int\nanswer = 42\n')
      curry.reset(backend='cxx', interpret='all', jit='off')
      module = curry.import_(source)
      self.assertEqual(curry.eval(module.answer).one(), 42)
      self.assertNotIn('ImageVanishedHelper', image.read(image.filename(source))['imports'])

  def test_foreign_budget_never_publishes(self):
    prelude = curry.import_('Prelude')
    shared = image.filename(getHandle(prelude).icurry.filename)
    before = image.digest(shared)
    budget = image.read(shared)['budget']
    with tempfile.TemporaryDirectory() as directory:
      source = os.path.join(directory, 'ImageForeign.curry')
      with open(source, 'w') as stream:
        stream.write('module ImageForeign where\nanswer :: Int\nanswer = 42\n')
      curry.reset(backend='cxx', interpret='all', jit='off', inline_budget=budget + 1)
      module = curry.import_(source)
      self.assertEqual(curry.eval(module.answer).one(), 42)
      self.assertFalse(os.path.exists(image.filename(source)))
      self.assertEqual(image.digest(shared), before)
      self.assertEqual(image.read(shared)['budget'], budget)

  def test_two_writers_translate_once(self):
    with tempfile.TemporaryDirectory() as directory:
      source = os.path.join(directory, 'ImageWriters.curry')
      with open(source, 'w') as stream:
        stream.write('module ImageWriters where\nanswer :: Int\nanswer = 42\n')
      curry.import_(source)
      os.unlink(image.filename(source))
      counter = os.path.join(directory, 'translations')
      script = """
import curry, sys, time
from curry.backends.cxx import image
curry.reset(backend='cxx', interpret='all', jit='off')
original = image.optimize
def optimize(interp, module, *args, **kwds):
  if module.fullname == 'ImageWriters':
    with open(sys.argv[2], 'a') as stream:
      stream.write('translation\\n')
    time.sleep(0.2)
  return original(interp, module, *args, **kwds)
image.optimize = optimize
module = curry.import_(sys.argv[1])
assert curry.eval(module.answer).one() == 42
"""
      children = [subprocess.Popen([sys.executable, '-c', script, source, counter],
          stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
      try:
        for child in children:
          stdout, stderr = child.communicate(timeout=120)
          self.assertEqual(child.returncode, 0, (stdout, stderr))
      finally:
        for child in children:
          if child.poll() is None:
            child.kill()
            child.wait()
      with open(counter) as stream:
        self.assertEqual(stream.read().splitlines(), ['translation'])
      self.assertEqual(image.read(image.filename(source))['source'], image.digest(source))

  def test_stamp_without_input_is_stale(self):
    from curry.backends.cxx import toolchain
    from curry import config
    with tempfile.TemporaryDirectory() as directory:
      source = os.path.join(directory, 'ImageStamp.curry')
      path = image.filename(source).removesuffix('.img') + '.so'
      os.makedirs(os.path.dirname(path))
      step = toolchain.Cpp2So(curry._interpreter_)
      with open(step.stampfile(path), 'w') as stream:
        stream.write('%s\n%s\n%s\n' % (step.digest(), config.prefix(),
            json.dumps({'version': 1, 'imports': {}})))
      self.assertFalse(step.stamp_is_current(path))

  def test_receipt_uses_translated_source(self):
    from curry.backends.cxx import toolchain
    with tempfile.TemporaryDirectory() as directory:
      source = os.path.join(directory, 'ImageReceipt.curry')
      with open(source, 'w') as stream:
        stream.write('module ImageReceipt where\nanswer :: Int\nanswer = 42\n')
      curry.import_(source)
      translated = image.digest(source)
      with open(source, 'a') as stream:
        stream.write('-- later edit\n')
      self.assertEqual(toolchain.input_record(curry._interpreter_, source)['source'],
          translated)

  def test_compiled_source_receipt_and_precedence(self):
    with tempfile.TemporaryDirectory() as directory:
      source = os.path.join(directory, 'ImagePrecedence.curry')
      def write(value):
        with open(source, 'w') as stream:
          stream.write('module ImagePrecedence where\nanswer :: Int\n'
              'answer = %d\n' % value)
      write(1)
      curry.reset(backend='cxx', interpret='off', jit='off')
      module = curry.import_(source)
      self.assertIsNotNone(getHandle(module).sofilename)
      self.assertEqual(curry.eval(module.answer).one(), 1)
      from curry.toolchain import _filenames
      plain, zipped = _filenames.jsonfilenames(source)
      with open(zipped, 'rb') as stream:
        data = zlib.decompress(stream.read())
      with open(plain, 'wb') as stream:
        stream.write(data)
      write(2)
      # Content receipts also reject objects after timestamp-preserving edits.
      os.utime(source, (1000000000, 1000000000))
      curry.reset(backend='cxx', interpret='all', jit='off')
      module = curry.import_(source)
      self.assertEqual(curry.eval(module.answer).one(), 2)
      saved = os.path.join(directory, 'saved.cpp')
      curry._interpreter_.save(module, saved, module_main=False)
      with open(saved) as stream:
        self.assertIn('Arg(2)', stream.read())
      curry.reset(backend='cxx', interpret='new', jit='off')
      module = curry.import_(source)
      self.assertIsNone(getHandle(module).sofilename)
      self.assertEqual(curry.eval(module.answer).one(), 2)
      curry.reset(backend='cxx', interpret='off', jit='off')
      module = curry.import_(source)
      self.assertEqual(curry.eval(module.answer).one(), 2)
      from curry.toolchain import _filenames
      for product in _filenames.jsonfilenames(source):
        if os.path.exists(product):
          os.utime(product, (2000000000, 2000000000))
      curry.reset(backend='cxx', interpret='new', jit='off')
      module = curry.import_(source)
      self.assertIsNotNone(getHandle(module).sofilename)
      self.assertEqual(curry.eval(module.answer).one(), 2)

  def test_parent_imports_child_symbol(self):
    with tempfile.TemporaryDirectory() as directory:
      os.mkdir(os.path.join(directory, 'ImageParent'))
      source = os.path.join(directory, 'ImageParent.curry')
      child = os.path.join(directory, 'ImageParent', 'Child.curry')
      with open(child, 'w') as stream:
        stream.write('module ImageParent.Child where\nvalue :: Int\nvalue = 42\n')
      with open(source, 'w') as stream:
        stream.write('module ImageParent where\nimport ImageParent.Child\n'
            'answer :: Int\nanswer = value\n')
      for _ in range(2):
        curry.reset(backend='cxx', interpret='all', jit='off')
        module = curry.import_(source)
        self.assertEqual(curry.eval(module.answer).one(), 42)

  def test_from_text(self):
    module = curry.compile('answer :: Int\nanswer = 42\n')
    path = image.filename(getHandle(module).icurry.filename)
    self.assertEqual(image.read(path)['name'], module.__name__)
    self.assertEqual(curry.eval(module.answer).one(), 42)
    self.assertIn("'I', 42", inspect.getimpl(module.answer))

  def test_translation_reads_aot_import_image(self):
    curry.reset(backend='cxx', interpret='new', jit='off')
    prelude = curry.import_('Prelude')
    self.assertIsNotNone(getHandle(prelude).sofilename)
    image._import_images(curry._interpreter_, ['Prelude'], None)
    original = image._loadcurry.loadjson
    def own_json(path):
      self.assertNotEqual(os.path.basename(path), 'Prelude.json.z')
      self.assertNotEqual(os.path.basename(path), 'Prelude.json')
      return original(path)
    with mock.patch.object(image.curryrt, 'load_image',
        wraps=image.curryrt.load_image) as reader, \
        mock.patch.object(image._loadcurry, 'loadjson', side_effect=own_json):
      module = curry.compile('answer :: Int\nanswer = id 42\n')
    self.assertEqual(curry.eval(module.answer).one(), 42)
    self.assertTrue(any(call.kwargs.get('attach_code') is False
        for call in reader.call_args_list))
    self.assertIsNotNone(getHandle(prelude).sofilename)


if __name__ == '__main__':
  cytest.main()

'''The native module image and its content receipts.'''
import cytest # from ./lib; must be first
import curry
from curry import inspect, toolchain
from curry.backends.cxx import image, curryrtbindings as curryrt
from curry.objects.handle import getHandle
from unittest import mock
import os
import json
import subprocess
import sys
import struct
import tempfile


class TestImage(cytest.TestCase):
  def setUp(self):
    curry.reset(backend='cxx', interpret='all', jit='off')

  def test_shared_lock_refusal_imports_privately(self):
    from curry.toolchain import _productlock
    with tempfile.TemporaryDirectory() as directory:
      source = os.path.join(directory, 'ImageLockRefused.curry')
      with open(source, 'w') as stream:
        stream.write('module ImageLockRefused where\nanswer :: Int\nanswer = 42\n')
      icyfile = toolchain.curry2icurry(source, curry.path)
      shared = os.path.realpath(_productlock.lockfile(icyfile))
      opening = _productlock._open
      refused = []
      def refuse_shared(path):
        if path == shared:
          refused.append(path)
          return None
        return opening(path)
      with mock.patch.object(_productlock, '_open', side_effect=refuse_shared):
        module = curry.import_(source)
      self.assertEqual(curry.eval(module.answer).one(), 42)
      self.assertTrue(refused)
      self.assertFalse(os.path.exists(image.filename(source)))
      self.assertNotEqual(getHandle(module).icurry._loaded_generation.image,
          image.filename(source))

  def test_completion_checked_once_per_load(self):
    from curry.toolchain import _curry2icurry
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=os.name == 'nt') as directory:
      source = os.path.join(directory, 'ImageCompletionOnce.curry')
      with open(source, 'w') as stream:
        stream.write('module ImageCompletionOnce where\nanswer :: Int\nanswer = 42\n')
      curry.reset(interpret='off', jit='off')
      curry.import_(source)
      check = _curry2icurry.product_receipts
      for mode in ('all', 'off'):
        with self.subTest(interpret=mode):
          curry.reset(interpret=mode, jit='off')
          with mock.patch.object(_curry2icurry, 'product_receipts', wraps=check) as checks:
            module = curry.import_(source)
          own = [call for call in checks.call_args_list
              if call.args[0].endswith('ImageCompletionOnce.icy')]
          self.assertEqual(len(own), 1)
          self.assertEqual(curry.eval(module.answer).one(), 42)
      self.assertIsNone(_curry2icurry._load_completions.get())

  def test_icurry_replaced_after_parse(self):
    from curry.toolchain import _loadcurry
    with tempfile.TemporaryDirectory() as directory:
      source = os.path.join(directory, 'ImageParseRace.curry')
      with open(source, 'w') as stream:
        stream.write('module ImageParseRace where\nanswer :: Int\nanswer = 41\n')
      icyfile = toolchain.curry2icurry(source, curry.path)
      with open(icyfile) as stream:
        original = stream.read()
      replacement = original.replace('41', '42')
      self.assertNotEqual(original, replacement)
      load = _loadcurry.loadicurry
      def replace_after_parse(path):
        raw = load(path)
        image.cache.write_file(icyfile, replacement)
        return raw
      with mock.patch.object(_loadcurry, 'loadicurry', side_effect=replace_after_parse):
        image.ensure(curry._interpreter_, icyfile)
      module = curry._interpreter_.import_(image.load(curry._interpreter_, icyfile))
      self.assertEqual(curry.eval(module.answer).one(), 42)

  def test_summary_declarations_are_lazy(self):
    module = curry.import_('Prelude')
    raw = getHandle(module).icurry
    path = image.filename(raw.filename)
    bom = curryrt.load_image(getHandle(module).backend_handle, path,
        json.dumps(image.read(path), sort_keys=True, separators=(',', ':')),
        attach_code=False)
    summary = image._from_bom(bom, raw.filename)
    self.assertEqual(summary.functions.loaded, {})
    from curry.icurry.analysis.inlining import recursive_functions
    self.assertEqual(recursive_functions(summary), frozenset())
    self.assertEqual(summary.functions.loaded, {})
    function = summary.functions['not']
    self.assertEqual(function.fullname, 'Prelude.not')
    self.assertIs(summary.functions['not'], function)
    self.assertEqual(list(summary.functions.loaded), ['not'])
    self.assertEqual(function.metadata['all.inline_body'],
        raw.functions['not'].metadata['all.inline_body'])

  def test_current_compile_writes_no_products(self):
    with tempfile.TemporaryDirectory() as directory:
      source = os.path.join(directory, 'ImageWarmCompile.curry')
      with open(source, 'w') as stream:
        stream.write('module ImageWarmCompile where\nanswer :: Int\nanswer = 42\n')
      module = curry.import_(source)
      icyfile = toolchain.icurryfilename(source)
      with mock.patch.object(image.cache, 'write_file',
          side_effect=AssertionError('current compile rewrote a product')) as writes:
        with mock.patch.object(image, 'read', side_effect=AssertionError('loaded image reopened')):
          image.ensure(curry._interpreter_, icyfile)
          self.assertIs(image.load(curry._interpreter_, icyfile), getHandle(module).icurry)
          self.assertIs(image.current(curry._interpreter_, source), getHandle(module).icurry)
        plan = toolchain.plans.makeplan(curry._interpreter_, toolchain.plans.MAKE_ICURRY
            | toolchain.plans.MAKE_IMAGE)
        toolchain.makecurry(plan, source, curry.path, is_sourcefile=True)
      self.assertEqual(writes.call_count, 0)

  def test_staleness_uses_loaded_import_digest(self):
    from curry.toolchain._icurry2image import ICurry2Image
    with tempfile.TemporaryDirectory() as directory:
      leaf = os.path.join(directory, 'ImageReceiptLeaf.curry')
      probe = os.path.join(directory, 'ImageReceiptProbe.curry')
      with open(leaf, 'w') as stream:
        stream.write('module ImageReceiptLeaf where\nanswer :: Int\nanswer = 1\n')
      module = curry.import_(leaf)
      with open(leaf, 'w') as stream:
        stream.write('module ImageReceiptLeaf where\nanswer :: Int\nanswer = 2\n')
      with open(probe, 'w') as stream:
        stream.write('module ImageReceiptProbe where\nimport ImageReceiptLeaf\nvalue :: Int\nvalue = answer\n')
      code = "import curry; curry.reset(interpret='all', jit='off'); curry.path.insert(0, %r); curry.import_(%r)" % (directory, probe)
      result = subprocess.run([sys.executable, '-c', code], capture_output=True,
          text=True, timeout=120)
      self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
      step = ICurry2Image(curry._interpreter_)
      search = [directory] + list(curry.path)
      with mock.patch('curry.toolchain._findcurry.loaded_generation', return_value=None):
        self.assertFalse(step.is_stale(image.filename(probe), search))
      self.assertTrue(step.is_stale(image.filename(probe), search))
      self.assertEqual(curry.eval(module.answer).one(), 1)

  def test_prelude(self):
    module = curry.import_('Prelude')
    path = image.filename(getHandle(module).icurry.filename)
    self.assertEqual(image.read(path)['name'], 'Prelude')
    curry.reset(backend='cxx', interpret='all', jit='off')
    with mock.patch('curry.toolchain._loadcurry.loadicurry',
        side_effect=AssertionError('image load read ICurry text')):
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
        path = image._path(curry._interpreter_, source)
        self.assertEqual(image.read(path)['source'], image.digest(toolchain.icurryfilename(source)))
      curry.reset(backend='cxx', interpret='all', jit='off')
      with mock.patch('curry.toolchain._loadcurry.loadicurry',
          side_effect=AssertionError('image load read ICurry text')):
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
      path = image._path(curry._interpreter_, source)
      self.assertNotEqual(image.digest(path), first)
      curry.reset(backend='cxx', interpret='all', jit='off', inline_budget=0)
      module = curry.import_(source)
      self.assertNotEqual(image.read(path)['budget'], 0)
      self.assertEqual(image.read(image._path(curry._interpreter_, source))['budget'], 0)
      self.assertEqual(curry.eval(module.answer).one(), 43)
      curry.reset(backend='cxx', interpret='all', jit='off', inline_budget=0)
      with mock.patch('curry.toolchain._loadcurry.loadicurry',
          side_effect=AssertionError('image load read ICurry text')):
        module = curry.import_(source)
      self.assertEqual(curry.eval(module.answer).one(), 43)

  def test_readonly_private_image(self):
    with tempfile.TemporaryDirectory() as directory:
      source = os.path.join(directory, 'ImageReadonly.curry')
      with open(source, 'w') as stream:
        stream.write('module ImageReadonly where\nanswer :: Int\nanswer = 42\n')
      curry.import_(source)
      path = image.filename(source)
      os.unlink(path)
      curry.reset(backend='cxx', interpret='all', jit='off')
      with mock.patch.object(image, 'writable', return_value=False):
        module = curry.import_(source)
      self.assertEqual(curry.eval(module.answer).one(), 42)
      self.assertFalse(os.path.exists(path))
      private = image._private_path(curry._interpreter_, source)
      self.assertTrue(os.path.exists(private))

  def test_text_private_image(self):
    module = curry.compile('answer :: Int\nanswer = 42\n')
    source = getHandle(module).icurry.filename
    from curry.toolchain._str2module import is_temporary
    self.assertTrue(is_temporary(source))
    self.assertTrue(os.path.isfile(image._path(curry._interpreter_, source)))
    self.assertIsNotNone(curryrt.icurry_bytecode(getHandle(module).symbols['answer'].info))
    self.assertEqual(curry.eval(module.answer).one(), 42)

  def test_sprite_make_image(self):
    with tempfile.TemporaryDirectory() as directory:
      source = os.path.join(directory, 'ImageCommand.curry')
      with open(source, 'w') as stream:
        stream.write('module ImageCommand where\nanswer = True\n')
      subprocess.check_call(cytest.tool_command([curry.config.sprite_make(),
          '--image', source]), timeout=120)
      self.assertEqual(image.read(image.filename(source))['name'], 'ImageCommand')

  def test_import_image_changes_before_compile(self):
    from curry.backends.cxx import toolchain as cxx_toolchain
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=os.name == 'nt') as directory:
      source = os.path.join(directory, 'ImageCompileRetry.curry')
      dependency = os.path.join(directory, 'ImageCompileDependency.curry')
      with open(dependency, 'w') as stream:
        stream.write('module ImageCompileDependency where\nvalue :: Int\nvalue = 42\n')
      with open(source, 'w') as stream:
        stream.write('module ImageCompileRetry where\nimport ImageCompileDependency\n'
            'answer :: Int\nanswer = value\n')
      curry.reset(backend='cxx', interpret='off', jit='off')
      compile_object = cxx_toolchain.Cpp2So.__call__
      changed = []
      def compile_after_publication(step, path, *args, **kwds):
        if path.endswith('ImageCompileRetry.cpp') and not changed:
          imported = image.filename(dependency)
          with open(imported, 'rb') as stream:
            data = stream.read()
          header = image.read(imported)
          header['generation'] = 1
          encoded = json.dumps(header, sort_keys=True, separators=(',', ':')).encode('ascii')
          _, _, size = image.PREFIX.unpack_from(data)
          with open(imported, 'wb') as stream:
            stream.write(image.PREFIX.pack(image.MAGIC, image.VERSION, len(encoded))
                + encoded + data[image.PREFIX.size + size:])
          changed.append(imported)
        return compile_object(step, path, *args, **kwds)
      with mock.patch.object(cxx_toolchain.Cpp2So, '__call__', compile_after_publication):
        module = curry.import_(source)
      self.assertEqual(len(changed), 1)
      self.assertIsNotNone(getHandle(module).sofilename)
      self.assertEqual(curry.eval(module.answer).one(), 42)

  def test_module_without_file_has_no_image(self):
    from curry import icurry
    module = curry.compile('answer :: Int\nanswer = 42\n')
    raw = getHandle(module).icurry
    with mock.patch.object(raw, 'filename', None), \
        mock.patch.object(module, '.source_mtime', None):
      self.assertIsNone(image.filename(raw.filename))
      self.assertIsNone(image.write(curry._interpreter_, raw))
      self.assertEqual(image._import_images(curry._interpreter_, [raw.fullname], None),
          {raw.fullname: image.generation_digest(raw._loaded_generation)})
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
      self.assertNotIn('ImageVanishedHelper', image.read(image._path(curry._interpreter_, source))['imports'])

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

  def test_library_import_keeps_environment_budget_private(self):
    prelude = curry.import_('Prelude')
    source = getHandle(prelude).icurry.filename
    shared = image.filename(source)
    before = image.digest(shared)
    budget = image.read(shared)['budget'] + 1
    flags = 'backend:cxx,interpret:all,jit:off,inline_budget:%d' % budget
    with mock.patch.dict(os.environ, {'SPRITE_INTERPRETER_FLAGS': flags}):
      curry.reset(backend='cxx', interpret='all', jit='off', inline_budget=budget)
      from curry.backends.cxx import tiered
      self.assertFalse(tiered._foreign_flags(curry._interpreter_))
      private = image._path(curry._interpreter_, source)
      self.assertNotEqual(private, shared)
      self.assertEqual(image.read(private)['budget'], budget)
      self.assertEqual(image.digest(shared), before)

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
      self.assertEqual(image.read(image.filename(source))['source'], image.digest(toolchain.icurryfilename(source)))

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
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=os.name == 'nt') as directory:
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

  def test_current_object_outranks_a_newer_image(self):
    '''A current object loads under interpret:new whatever the image's time says.'''
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=os.name == 'nt') as directory:
      source = os.path.join(directory, 'ImageObjectWins.curry')
      with open(source, 'w') as stream:
        stream.write('module ImageObjectWins where\nanswer :: Int\nanswer = 2\n')
      curry.reset(backend='cxx', interpret='off', jit='off')
      module = curry.import_(source)
      self.assertIsNotNone(getHandle(module).sofilename)
      self.assertEqual(curry.eval(module.answer).one(), 2)
      os.utime(image.filename(source), (2000000000, 2000000000))
      curry.reset(backend='cxx', interpret='new', jit='off')
      module = curry.import_(source)
      self.assertIsNotNone(getHandle(module).sofilename)
      self.assertEqual(curry.eval(module.answer).one(), 2)

  # Windows keeps the first object of a name mapped for the life of the
  # process; a recompiled object loads in the next process.
  @cytest.posix_only('a recompiled object replaces the mapped one in this process')
  def test_recompiled_object_replaces_the_mapped_one(self):
    with tempfile.TemporaryDirectory() as directory:
      source = os.path.join(directory, 'ImageRecompiled.curry')
      def write(value):
        with open(source, 'w') as stream:
          stream.write('module ImageRecompiled where\nanswer :: Int\n'
              'answer = %d\n' % value)
      write(1)
      curry.reset(backend='cxx', interpret='off', jit='off')
      module = curry.import_(source)
      self.assertEqual(curry.eval(module.answer).one(), 1)
      write(2)
      os.utime(source, (1000000000, 1000000000))
      curry.reset(backend='cxx', interpret='off', jit='off')
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

  def test_translation_uses_loaded_aot_summaries(self):
    curry.reset(backend='cxx', interpret='new', jit='off')
    prelude = curry.import_('Prelude')
    self.assertIsNotNone(getHandle(prelude).sofilename)
    image._import_images(curry._interpreter_, ['Prelude'], None)
    original = image._loadcurry.loadicurry
    def own_json(path):
      self.assertNotEqual(os.path.basename(path), 'Prelude.icy')
      return original(path)
    with mock.patch.object(image.curryrt, 'load_image',
        wraps=image.curryrt.load_image) as reader, \
        mock.patch.object(image._loadcurry, 'loadicurry', side_effect=own_json):
      module = curry.compile('answer :: Int\nanswer = id 42\n')
    self.assertEqual(curry.eval(module.answer).one(), 42)
    self.assertFalse(any(call.kwargs.get('attach_code') is False
        for call in reader.call_args_list))
    self.assertIsNotNone(getHandle(prelude).sofilename)


if __name__ == '__main__':
  cytest.main()

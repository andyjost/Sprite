"""Regression sequences from the outside review of the module rules."""
import cytest # from ./lib; must be first
import curry
from curry import config
from pathlib import Path
import os, shutil, subprocess, sys, tempfile, textwrap


class TestModuleReview(cytest.TestCase):
  def setUp(self):
    super().setUp()
    self.work = tempfile.TemporaryDirectory()
    self.addCleanup(self.work.cleanup)
    self.root = Path(self.work.name)

  def source(self, directory, name, text):
    path = self.root / directory / (name.replace('.', '/') + '.curry')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('module %s where\n%s\n' % (name, text), encoding='ascii')
    return path

  def child(self, code):
    code = "import os; os.environ['SPRITE_CACHE_FILE'] = ''\nroot = %r\n" % str(self.root) + textwrap.dedent(code)
    result = cytest.run_in_subprocess(code, timeout=180, address_space=4 << 30)
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    return result

  def test_01_saved_dependency_provenance(self):
    for directory, value in [('old', 1), ('new', 2)]:
      self.source(directory, 'Leaf', 'answer :: Int\nanswer = %d' % value)
    self.source('old', 'Main', 'import Leaf\nanswer :: Int\nanswer = Leaf.answer')
    self.child('''
      import curry, os
      curry.reset(interpret='off', jit='off')
      curry.path.insert(0, os.path.join(root, 'old'))
      module = curry.import_('Main')
      curry.save(module, os.path.join(root, 'saved' + curry.config.module_object_suffix()))
    ''')
    self.child('''
      import curry, os
      curry.reset(interpret='off', jit='off')
      curry.path.insert(0, os.path.join(root, 'old'))
      module = curry._interpreter_.load(os.path.join(root, 'saved' + curry.config.module_object_suffix()))
      assert curry.eval(module.answer).one() == 1
    ''')
    self.child('''
      import curry, os
      curry.reset(interpret='off', jit='off')
      curry.path.insert(0, os.path.join(root, 'new'))
      try:
        curry._interpreter_.load(os.path.join(root, 'saved' + curry.config.module_object_suffix()))
      except curry.LoadError as error:
        assert 'dependencies changed' in str(error), error
      else:
        raise AssertionError('saved object accepted changed dependency')
    ''')

  def test_01_saved_dependency_rebuild_from_path(self):
    self.test_01_saved_dependency_provenance()
    for mode in ('new', 'off'):
      for product in (self.root / 'new').rglob('*' + config.module_object_suffix()):
        product.unlink()
      self.child('''
        import curry, os
        curry.reset(interpret=%r, jit='off')
        curry.path[:0] = [os.path.join(root, d) for d in ('new', 'old')]
        module = curry._interpreter_.load(os.path.join(root, 'saved' + curry.config.module_object_suffix()))
        assert curry.eval(module.answer).one() == 2
      ''' % mode)

  def test_01_saved_dependency_missing_record(self):
    self.test_01_saved_dependency_provenance()
    record = self.root / ('saved' + config.module_object_suffix() + '.imports')
    for contents in (None, '{}', '{invalid', '{"version":1,"identity":"x","imports":{"Leaf":2}}'):
      if contents is None:
        record.unlink()
      else:
        record.write_text(contents)
      self.child('''
        import curry, os
        curry.reset(interpret='new', jit='off')
        curry.path.insert(0, os.path.join(root, 'new'))
        try:
          curry._interpreter_.load(os.path.join(root, 'saved' + curry.config.module_object_suffix()))
        except curry.LoadError:
          pass
        else:
          raise AssertionError('saved object accepted invalid or missing record')
      ''')
      for mode in ('new', 'off'):
        self.child('''
          import curry, os
          curry.reset(interpret=%r, jit='off')
          curry.path[:0] = [os.path.join(root, d) for d in ('new', 'old')]
          module = curry._interpreter_.load(os.path.join(root, 'saved' + curry.config.module_object_suffix()))
          assert curry.eval(module.answer).one() == 2
        ''' % mode)

  def test_02_named_import_path(self):
    self.named_import_path('frontend')

  def test_02_external_named_import_path(self):
    if config.icurry_tool() is None:
      self.skipTest('the optional ICurry translator is unavailable')
    self.named_import_path('icurry')

  def named_import_path(self, route):
    self.source('first', 'Leaf', 'f :: Int -> Int\nf x = x')
    self.source('second', 'Leaf', 'f :: Bool -> Bool\nf x = x')
    self.source('second', 'Main', 'import Leaf\nanswer :: Int\nanswer = f 1')
    self.child('''
      import curry, os
      curry.reset(interpret='new', jit='off')
      curry.path[:0] = [os.path.join(root, d) for d in ('first', 'second')]
      os.environ['SPRITE_CURRY2ICURRY'] = %r
      module = curry.import_('Main')
      assert str(curry.eval(module.answer).one()) == '1'
    ''' % route)

  def stale_translation(self, remove_source, standalone=False):
    self.source('project', 'Leaf', 'f :: Int -> Int\nf x = x')
    main = self.source('project', 'Main', 'import Leaf\nanswer :: Int\nanswer = f 1')
    self.child('''
      import curry, os
      curry.reset(interpret='new', jit='off')
      curry.path.insert(0, os.path.join(root, 'project'))
      curry.import_('Main')
    ''')
    if remove_source:
      main.unlink()
    from curry.toolchain import _filenames
    icy = Path(_filenames.icurryfilename(str(main)))
    if standalone:
      target = self.root / 'standalone' / 'Main.icy'
      target.parent.mkdir()
      for suffix in ('', '.imports'):
        shutil.copyfile(str(icy) + suffix, str(target) + suffix)
      for suffix in ('.fint', '.icurry'):
        shutil.copyfile(icy.with_suffix(suffix), target.with_suffix(suffix))
      icy = target
    self.source('project', 'Leaf', 'f :: Bool -> Bool\nf x = x')
    self.child('''
      import curry, os
      from curry.backends.cxx import image
      from curry.toolchain import _filenames
      curry.reset(interpret='new', jit='off')
      curry.path.insert(0, os.path.join(root, 'project'))
      curry.import_('Leaf')
      icy = %r
      try:
        image.ensure(curry._interpreter_, icy, curry.path)
      except (curry.CompileError, curry.ModuleLookupError, ValueError):
        pass
      else:
        raise AssertionError('stale ICurry accepted')
    ''' % str(icy))

  def test_03_source_free_receipt(self):
    self.stale_translation(True)

  def test_03_explicit_receipt(self):
    self.stale_translation(False)

  def test_03_standalone_receipt(self):
    self.stale_translation(True, standalone=True)

  @cytest.posix_only('POSIX directory permission bits')
  def test_06_readonly_translation(self):
    self.source('project', 'Leaf', 'f :: Int -> Int\nf x = x')
    main = self.source('project', 'Main', 'import Leaf\nanswer :: Int\nanswer = f 1')
    self.child('''
      import curry, os
      curry.reset(interpret='new', jit='off')
      curry.path.insert(0, os.path.join(root, 'project'))
      curry.import_('Main')
    ''')
    self.source('project', 'Leaf', 'f :: Int -> Int\nf x = x + 1')
    # A changed implementation alone can leave translation current. Remove
    # its receipt to require a translation rebuild in the read-only slot.
    from curry.toolchain import _filenames
    product = Path(_filenames.icurryfilename(str(main)))
    Path(str(product) + '.imports').unlink()
    product.parent.chmod(0o555)
    self.addCleanup(product.parent.chmod, 0o755)
    self.child('''
      import curry, os
      from curry.objects.handle import getHandle
      curry.reset(interpret='new', jit='off')
      curry.path.insert(0, os.path.join(root, 'project'))
      module = curry.import_('Main')
      assert str(curry.eval(module.answer).one()) == '2'
      source = getHandle(module).icurry.filename
      assert not source.startswith(os.path.join(root, 'project')), source
    ''')

  def test_07_parallel_file_scope(self):
    self.source('project', 'Leaf', 'answer :: Int\nanswer = 1')
    main = self.source('project', 'Main', 'import Leaf\nanswer :: Int\nanswer = Leaf.answer')
    self.child('''
      import os, subprocess, sys
      result = subprocess.run([sys.executable, '-m', 'curry.tools.make',
          '--jobs', '2', '--image', os.path.join(root, 'project', 'Main.curry')],
          cwd=root, capture_output=True, text=True)
      assert result.returncode == 0, result.stdout + result.stderr
    ''')

  def test_08_reload_loaded_dependency(self):
    self.source('first', 'Leaf', 'f :: Int -> Int\nf x = x')
    self.source('second', 'Leaf', 'f :: Bool -> Bool\nf x = x')
    self.source('project', 'Main', 'import Leaf\nanswer :: Int\nanswer = f 1')
    self.child('''
      import curry, os
      curry.reset(interpret='new', jit='off')
      curry.path[:0] = [os.path.join(root, d) for d in ('first', 'project')]
      curry.import_('Leaf')
      module = curry.import_('Main')
      curry.path.insert(0, os.path.join(root, 'second'))
      curry.reload(module)
      assert str(curry.eval(module.answer).one()) == '1'
    ''')

  def test_10_reserved_copy_requires_provenance(self):
    with tempfile.TemporaryDirectory(prefix='sprite-tiered-') as work:
      target = Path(work) / 'private0' / 'Control' / 'SetFunctions.curry'
      target.parent.mkdir(parents=True)
      shutil.copyfile(config.installed_path('curry', 'Control/SetFunctions.curry'), target)
      import hashlib, json
      Path(str(target) + '.sprite-input').write_text(json.dumps(dict(
          version=1, name='Control.SetFunctions',
          digest=hashlib.sha256(target.read_bytes()).hexdigest())))
      self.child('''
        import curry
        curry.reset(interpret='new', jit='off')
        curry.path.insert(0, %r)
        try:
          curry.import_('Control.SetFunctions')
        except curry.ModuleLookupError:
          pass
        else:
          raise AssertionError('unauthenticated reserved copy accepted')
      ''' % str(target.parent.parent))

  def library_layout(self):
    source = self.source('library', 'ReviewLibrary', 'answer :: Int\nanswer = 1')
    self.child('''
      import curry, os
      curry.reset(interpret='new', jit='off')
      curry.import_(os.path.join(root, 'library', 'ReviewLibrary.curry'))
    ''')
    return source

  def test_04_importer_keeps_writable_installation(self):
    source = self.library_layout()
    from curry.toolchain import _filenames
    Path(_filenames.replacesuffix(str(source), '.img')).unlink()
    self.child('''
      import curry, os
      from unittest import mock
      from curry.toolchain import _findcurry, _filenames
      from curry.backends.cxx import image
      from curry.objects.handle import getHandle
      curry.reset(interpret='new', jit='off')
      source = os.path.join(root, 'library', 'ReviewLibrary.curry')
      original = _findcurry._installed_library_file
      def installed(path):
        return bool(path) and (os.path.realpath(path).startswith(
            os.path.join(root, 'library') + os.sep) or original(path))
      with mock.patch.object(_findcurry, '_installed_library_file', installed):
        module = curry.import_(source)
        path = image._path(curry._interpreter_, getHandle(module).icurry.filename)
        assert not path.startswith(os.path.join(root, 'library') + os.sep), path
      assert not os.path.exists(image.filename(source))
      assert curry.eval(module.answer).one() == 1
    ''')

  def test_04_explicit_writer_keeps_writable_installation(self):
    source = self.library_layout()
    from curry.toolchain import _filenames
    Path(_filenames.replacesuffix(str(source), '.img')).unlink()
    self.child('''
      import curry, os
      from unittest import mock
      from curry.toolchain import _findcurry, _filenames, _curry2icurry
      from curry.backends.cxx import image, toolchain
      curry.reset(interpret='new', jit='off')
      source = os.path.join(root, 'library', 'ReviewLibrary.curry')
      original = _findcurry._installed_library_file
      def installed(path):
        return bool(path) and (os.path.realpath(path).startswith(
            os.path.join(root, 'library') + os.sep) or original(path))
      with mock.patch.object(_findcurry, '_installed_library_file', installed):
        icy = _curry2icurry.curry2icurry(source, curry.path, use_cache=False)
        assert icy == _filenames.icurryfilename(source)
        path, _ = image.ensure(curry._interpreter_, icy, curry.path)
        assert path == image.filename(source), path
        cpp = toolchain.ICurry2Cpp(curry._interpreter_)(path, curry.path)
        product = toolchain.Cpp2So(curry._interpreter_)(cpp, curry.path)
        assert os.path.isfile(product)
        assert product.startswith(os.path.join(root, 'library') + os.sep)
    ''')

  def test_05_writable_installed_llvm_slot(self):
    self.library_layout()
    self.child('''
      import curry, os
      from unittest import mock
      from curry.backends.cxx import llvmjit, image
      from curry.toolchain import _findcurry
      if llvmjit.available():
        curry.reset(interpret='all', jit='eager', jit_backend='llvm')
        source = os.path.join(root, 'library', 'ReviewLibrary.curry')
        original = _findcurry._installed_library_file
        def installed(path):
          return bool(path) and (os.path.realpath(path).startswith(
              os.path.join(root, 'library') + os.sep) or original(path))
        with mock.patch.object(_findcurry, '_installed_library_file', installed):
          module = curry.import_(source)
          assert curry.eval(module.answer).one() == 1
        assert os.path.isfile(os.path.splitext(image.filename(source))[0] + '.jit')
    ''')

  def test_attached_image_survives_atomic_publication(self):
    self.source('project', 'Published', 'answer :: Int\nanswer = 1')
    self.child('''
      import curry, os, subprocess, sys
      from pathlib import Path
      from curry.backends.cxx import image
      curry.reset(interpret='all', jit='off')
      source = os.path.join(root, 'project', 'Published.curry')
      module = curry.import_(source)
      path = image.filename(source)
      before = image.digest(path)
      Path(source).write_text('module Published where\\nanswer :: Int\\nanswer = 2\\n')
      code = "import curry; curry.reset(interpret='all', jit='off'); m = curry.import_(%r); assert curry.eval(m.answer).one() == 2" % source
      result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
      assert result.returncode == 0, result.stdout + result.stderr
      assert image.digest(path) != before
      assert curry.eval(module.answer).one() == 1
    ''')

  def test_04_importer_translation_and_object_are_private(self):
    source = self.library_layout()
    from curry.toolchain import _filenames
    Path(_filenames.icurryfilename(str(source)) + '.imports').unlink()
    self.child('''
      import curry, hashlib, os
      from pathlib import Path
      from unittest import mock
      from curry.toolchain import _findcurry
      from curry.objects.handle import getHandle
      source = os.path.join(root, 'library', 'ReviewLibrary.curry')
      directory = Path(source).parent
      def products():
        return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*') if p.is_file()}
      before = products()
      original = _findcurry._installed_library_file
      def installed(path):
        return bool(path) and (os.path.realpath(path).startswith(
            str(directory) + os.sep) or original(path))
      curry.reset(interpret='off', jit='off')
      with mock.patch.object(_findcurry, '_installed_library_file', installed):
        module = curry.import_(source)
        assert curry.eval(module.answer).one() == 1
        assert not getHandle(module).sofilename.startswith(str(directory) + os.sep)
      assert products() == before, 'importer wrote installed products'
    ''')

  @cytest.posix_only('the development precompiled header uses a POSIX compiler')
  def test_04_development_pch_writer(self):
    self.child('''
      import curry, os, shutil
      from unittest import mock
      from curry import config
      from curry.backends.cxx import toolchain
      include = os.path.join(root, 'include')
      shutil.copytree(config.installed_path('include'), include,
          ignore=shutil.ignore_patterns('*.gch'))
      original = config.installed_path
      def installed(*parts):
        return os.path.join(root, *parts) if parts[0] == 'include' else original(*parts)
      os.environ.pop('SPRITE_CXX_PCH_ROOT', None)
      with mock.patch.object(config, 'installed_path', installed), \\
          mock.patch.object(config, 'in_conda_prefix', return_value=False), \\
          mock.patch.object(config, '_is_wheel_install', return_value=False):
        assert config.cxx_pch_root() == include
        step = toolchain.Cpp2So(curry._interpreter_)
        header = step._header()
        assert not os.path.exists(header.filename)
        assert header.prepare()
        assert os.path.isfile(header.filename)
        assert header.filename.startswith(include + os.sep)
    ''')

  def test_07_parallel_named_scope(self):
    self.source('first', 'Leaf', 'f :: Int -> Int\nf x = x')
    self.source('second', 'Leaf', 'f :: Bool -> Bool\nf x = x')
    self.source('second', 'Main', 'import Leaf\nanswer :: Int\nanswer = f 1')
    self.child('''
      import os, subprocess, sys
      env = dict(os.environ, CURRYPATH=os.pathsep.join(
          os.path.join(root, d) for d in ('first', 'second')))
      result = subprocess.run([sys.executable, '-m', 'curry.tools.make',
          '--jobs', '2', '--image', 'Main'], cwd=root, env=env,
          capture_output=True, text=True)
      assert result.returncode == 0, result.stdout + result.stderr
    ''')

  def test_01_executable_external_dependency(self):
    for directory, value in [('old', 1), ('new', 2)]:
      self.source(directory, 'Leaf', 'answer :: Int\nanswer = %d' % value)
    self.source('old', 'Main', 'import Leaf\nanswer :: Int\nanswer = Leaf.answer')
    self.child('''
      import curry, os
      from unittest import mock
      from curry.toolchain import _findcurry
      curry.reset(interpret='off', jit='off')
      curry.path.insert(0, os.path.join(root, 'old'))
      module = curry.import_('Main')
      original = _findcurry._installed_library_file
      leaf = os.path.join(root, 'old', 'Leaf.curry')
      with mock.patch.object(_findcurry, '_installed_library_file',
          lambda path: path == leaf or original(path)):
        curry.save(module, os.path.join(root, 'saved.exe' if os.name == 'nt' else 'saved'), main='answer')
    ''')
    self.child('''
      import curry, os, subprocess, sys
      curry.reset(interpret='off', jit='off')
      curry.path.insert(0, os.path.join(root, 'new'))
      curry.import_('Leaf')
      env = dict(os.environ, CURRYPATH=os.path.join(root, 'new'))
      program = os.path.join(root, 'saved.exe' if os.name == 'nt' else 'saved')
      command = [program] if os.name == 'nt' else [sys.executable, program]
      result = subprocess.run(command, env=env, capture_output=True, text=True)
      assert result.returncode != 0, result.stdout
      assert 'dependencies changed' in result.stderr, result.stderr
    ''')

  def test_batch_installed_images_follow_dependency_order(self):
    self.source('library', 'Leaf', 'answer :: Int\nanswer = 1')
    self.source('library', 'Main', 'import Leaf\nanswer :: Int\nanswer = Leaf.answer')
    self.child('''
      import curry, os
      from unittest import mock
      from curry.toolchain import _findcurry
      from curry.tools import make
      from curry.backends.cxx import image
      directory = os.path.join(root, 'library')
      os.environ['CURRYPATH'] = directory
      curry.config.currypath(reset=True)
      original = _findcurry._installed_library_file
      def installed(path):
        return bool(path) and (os.path.realpath(path).startswith(
            directory + os.sep) or original(path))
      with mock.patch.object(_findcurry, '_installed_library_file', installed):
        make.main('sprite-make', ['--image', 'Main', 'Leaf'])
      for name in ('Main', 'Leaf'):
        assert os.path.isfile(image.filename(os.path.join(directory, name + '.curry'))), name
    ''')

  def test_02_named_lookup_path_keeps_interpreter_imports(self):
    self.source('first', 'Leaf', 'f :: Int -> Int\nf x = x')
    self.source('second', 'Leaf', 'f :: Bool -> Bool\nf x = x')
    self.source('second', 'Main', 'import Leaf\nanswer :: Int\nanswer = f 1')
    self.child('''
      import curry, os
      curry.reset(interpret='new', jit='off')
      curry.path.insert(0, os.path.join(root, 'first'))
      module = curry.import_('Main', path=[os.path.join(root, 'second')])
      assert curry.eval(module.answer).one() == 1
    ''')

  def test_batch_images_keep_foreign_budget_private(self):
    self.source('project', 'Leaf', 'answer :: Int\nanswer = 1')
    self.source('project', 'Main', 'import Leaf\nanswer :: Int\nanswer = Leaf.answer')
    self.child('''
      import curry, os
      from curry.tools import make
      from curry.backends.cxx import image
      from curry.toolchain import _filenames
      directory = os.path.join(root, 'project')
      os.environ['CURRYPATH'] = directory
      curry.config.currypath(reset=True)
      budget = curry.flags['inline_budget'] + 1
      curry.reset(interpret='new', jit='off', inline_budget=budget)
      make.main('sprite-make', ['--image', 'Main', 'Leaf'])
      for name in ('Main', 'Leaf'):
        source = os.path.join(directory, name + '.curry')
        assert os.path.isfile(_filenames.icurryfilename(source))
        assert not os.path.exists(image.filename(source)), name
    ''')

  def test_01_saved_object_preserves_linker_bytes(self):
    self.source('project', 'Main', 'answer :: Int\nanswer = 1')
    self.child('''
      import curry, os
      from pathlib import Path
      from unittest import mock
      from curry.backends.cxx.toolchain import Cpp2So
      curry.reset(interpret='off', jit='off')
      curry.path.insert(0, os.path.join(root, 'project'))
      module = curry.import_('Main')
      linked = []
      original = Cpp2So.__call__
      def capture(self, *args, **kwds):
        product = original(self, *args, **kwds)
        linked.append(Path(product).read_bytes())
        return product
      target = os.path.join(root, 'saved' + curry.config.module_object_suffix())
      with mock.patch.object(Cpp2So, '__call__', capture):
        curry.save(module, target)
      assert linked and Path(target).read_bytes() == linked[-1], 'saved object changed after linking'
    ''')

  def test_02_rewrite_named_import_path(self):
    self.source('first', 'Leaf', 'f :: Int -> Int\nf x = x')
    self.source('second', 'Leaf', 'f :: Bool -> Bool\nf x = x')
    self.source('second', 'Main', 'import Leaf\nanswer :: Int\nanswer = f 1')
    self.child('''
      import os, subprocess, sys
      env = dict(os.environ, CURRYPATH=os.pathsep.join(
          os.path.join(root, d) for d in ('first', 'second')))
      result = subprocess.run([sys.executable, '-m', 'curry.tools.make',
          '--rewrite-flat', 'Main'], cwd=root, env=env, capture_output=True, text=True)
      assert result.returncode == 0, result.stdout + result.stderr
    ''')

  def test_02_external_lookup_only_path(self):
    if config.icurry_tool() is None:
      self.skipTest('the optional ICurry translator is unavailable')
    self.source('first', 'Leaf', 'f :: Int -> Int\nf x = x')
    self.source('second', 'Leaf', 'f :: Bool -> Bool\nf x = x')
    self.source('second', 'Main', 'import Leaf\nanswer :: Int\nanswer = f 1')
    self.child('''
      import curry, os
      curry.reset(interpret='new', jit='off')
      curry.path.insert(0, os.path.join(root, 'first'))
      os.environ['SPRITE_CURRY2ICURRY'] = 'icurry'
      module = curry.import_('Main', path=[os.path.join(root, 'second')])
      assert curry.eval(module.answer).one() == 1
    ''')

  @cytest.posix_only('executable preprocessor script')
  def test_relative_preprocessor(self):
    source = self.source('project', 'Main', 'answer :: Int\nanswer = 1')
    source.write_text('{-# OPTIONS_FRONTEND -F --pgmF=./preprocess #-}\n' + source.read_text())
    script = self.root / 'project' / 'preprocess'
    script.write_text('#!/bin/sh\ncp "$2" "$3"\n')
    script.chmod(0o755)
    self.child('''
      import curry, os
      os.chdir(os.path.join(root, 'project'))
      curry.reset(interpret='new', jit='off')
      try:
        curry.import_(os.path.abspath('Main.curry'))
      except curry.CompileError as error:
        assert './preprocess' in str(error), error
        assert 'Preprocessor exited with exit code' in str(error), error
      else:
        raise AssertionError('relative target preprocessor accepted')
    ''')

  def test_relative_configured_preprocessor(self):
    source = self.source('project', 'Main', 'answer :: Int\nanswer = 1')
    self.child('''
      import curry, os
      from unittest import mock
      curry.reset(interpret='new', jit='off')
      with mock.patch.object(curry.config, 'frontend_flags',
                             return_value='-F --pgmF=./preprocess'):
        try:
          curry.import_(os.path.join(root, 'project', 'Main.curry'))
        except curry.CompileError as error:
          assert './preprocess' in str(error), error
          assert 'Preprocessor exited with exit code' in str(error), error
        else:
          raise AssertionError('relative configured preprocessor accepted')
    ''')

  def test_qualified_readonly_dependency_after_edit(self):
    self.source('project', 'Main', 'answer :: Int\nanswer = 1')
    self.child('''
      import curry, os
      curry.reset(interpret='new', jit='off')
      curry.path.insert(0, os.path.join(root, 'project'))
      curry.import_('Main')
    ''')
    leaf = self.source('readonly', 'Leaf', 'answer :: Int\nanswer = 2')
    self.source('project', 'Main', 'import {- before qualifier -} qualified '
        '{- before name {- nested -} -} Leaf\nanswer :: Int\nanswer = Leaf.answer')
    leaf.parent.chmod(0o555)
    try:
      self.child('''
        import curry, os
        from curry.objects.handle import getHandle
        curry.reset(interpret='new', jit='off')
        curry.path[:0] = [os.path.join(root, d) for d in ('project', 'readonly')]
        module = curry.import_('Main')
        assert curry.eval(module.answer).one() == 2
        raw = getHandle(curry.import_('Leaf')).icurry
        assert not os.path.realpath(raw.filename).startswith(
            os.path.realpath(os.path.join(root, 'readonly')) + os.sep), raw.filename
        assert not os.path.exists(os.path.join(root, 'readonly', '.curry'))
      ''')
    finally:
      leaf.parent.chmod(0o755)

  def test_commented_frontend_options(self):
    self.source('project', 'Main',
        '-- {-# OPTIONS_FRONTEND -i./unused #-}\nanswer :: Int\nanswer = 42')
    self.child('''
      import curry, os
      curry.reset(interpret='new', jit='off')
      module = curry.import_(os.path.join(root, 'project', 'Main.curry'))
      assert curry.eval(module.answer).one() == 42
    ''')

  @cytest.posix_only('executable preprocessor script')
  def test_preprocessor_opaque_argument(self):
    for index, option in enumerate(('--optF -include', '--optF=-include')):
      directory = 'project%d' % index
      source = self.source(directory, 'Main', 'answer :: Int\nanswer = 1')
      script = source.parent / 'preprocess'
      source.write_text('{-# OPTIONS_FRONTEND -F --pgmF=%s %s #-}\n' % (script, option) + source.read_text())
      script.write_text('#!/bin/sh\n[ "$4" = "-include" ] || exit 42\ncp "$2" "$3"\n')
      script.chmod(0o755)
      self.child('''
        import curry, os
        os.chdir(os.path.join(root, %r))
        curry.reset(interpret='new', jit='off')
        module = curry.import_(os.path.abspath('Main.curry'))
        assert curry.eval(module.answer).one() == 1
      ''' % directory)

  def test_batch_independent_images_share_loaded_imports(self):
    self.source('project', 'First', 'answer :: Int\nanswer = 1')
    self.source('project', 'Second', 'answer :: Int\nanswer = 2')
    self.child('''
      import curry, os
      from unittest import mock
      from curry.tools import make
      from curry.interpreter import Interpreter
      directory = os.path.join(root, 'project')
      os.environ['CURRYPATH'] = directory
      curry.config.currypath(reset=True)
      original = Interpreter.reset
      resets = []
      def reset(interp, *args, **kwds):
        resets.append(True)
        return original(interp, *args, **kwds)
      with mock.patch.object(Interpreter, 'reset', reset):
        make.main('sprite-make', ['--image', 'First', 'Second'])
      # Construction resets once; independent targets need no further reset.
      assert len(resets) <= 1, 'independent targets discarded their loaded imports'
    ''')

  def test_01_saved_receipt_obeys_loaded_boundary(self):
    self.source('project', 'Main', 'answer :: Int\nanswer = 1')
    self.source('project', 'User', 'import Main\nanswer :: Int\nanswer = Main.answer')
    self.child('''
      import curry, os
      curry.reset(interpret='off', jit='off')
      curry.path.insert(0, os.path.join(root, 'project'))
      module = curry.import_('Main')
      curry.save(module, os.path.join(root, 'saved' + curry.config.module_object_suffix()))
    ''')
    self.child('''
      import curry, json, os
      from pathlib import Path
      curry.reset(interpret='off', jit='off')
      curry.path.insert(0, os.path.join(root, 'project'))
      curry._interpreter_.load(os.path.join(root, 'saved' + curry.config.module_object_suffix()))
      module = curry.import_('User')
      receipt = Path(root) / ('saved' + curry.config.module_object_suffix() + '.imports')
      record = json.loads(receipt.read_text())
      record['identity'] = '0' * 64
      receipt.write_text(json.dumps(record))
      try:
        curry.save(module, os.path.join(root, 'user' + curry.config.module_object_suffix()))
      except (ValueError, curry.CurryError) as error:
        assert 'changed since it was loaded' in str(error), error
      else:
        raise AssertionError('save read a changed loaded dependency receipt')
    ''')

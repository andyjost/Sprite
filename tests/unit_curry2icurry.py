import cytest # from ./lib; must be first
from curry import cache, config, exceptions, toolchain
from curry.toolchain import _curry2icurry, _frontend, plans
from curry.utility import binding
import curry, os, shutil, subprocess, tarfile, tempfile, unittest
from unittest import mock

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'curry')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAKE_ENV = {
    'PATH': os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin')
  , 'HOME': os.environ.get('HOME', '/')
  , 'LC_ALL': 'C.UTF-8'
  , 'TMPDIR': os.environ.get('TMPDIR', tempfile.gettempdir())
  }
SUBDIR = os.path.join('.curry', config.intermediate_subdir())
FE_SUBDIR = os.path.join('.curry', config.frontend_subdir())

def oracle_icy(directory, name):
  '''The ICurry file that icurry wrote for a test module, or None.'''
  path = os.path.join(DATA, directory, SUBDIR, name + '.icy')
  return path if os.path.isfile(path) else None

def readbytes(filename):
  with open(filename, 'rb') as istream:
    return istream.read()

def interfaces_beside(icyfile):
  '''The bytes of the interface files beside an ICurry file, by suffix.'''
  return {
      suffix: readbytes(cache.interface_filename(icyfile, suffix))
          for suffix in cache.INTERFACE_SUFFIXES
    }

class TestCurry2ICurry(cytest.TestCase):
  '''
  Tests for the route from Curry to ICurry through the Curry front end and
  the built-in translation.
  '''

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    if config.curry_frontend() is None:
      raise unittest.SkipTest('the Curry front end is not configured')

  def setUp(self):
    super().setUp()
    self.tmpdir = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
    self.addCleanup(shutil.rmtree, self.tmpdir, True)

  def copy(self, relpath):
    '''Copies a test module into the scratch directory.'''
    dst = os.path.join(self.tmpdir, relpath)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy(os.path.join(DATA, relpath), dst)
    return dst

  def without_cache(self):
    '''
    Turns the ICurry cache off for one test.  A hit in the cache writes the
    ICurry and its copies of the interfaces, not the files of the front end
    (section 1 of README), so a test of the front end's files runs without
    it.
    '''
    patcher = mock.patch.dict(os.environ, {'SPRITE_CACHE_FILE': ''})
    patcher.start()
    self.addCleanup(patcher.stop)
    cache.reset()
    self.addCleanup(cache.reset)

  def convert(self, curryfile, currypath=(), **kwds):
    kwds.setdefault('curry2icurry', 'frontend')
    kwds.setdefault('quiet', True)
    return toolchain.curry2icurry(curryfile, list(currypath), **kwds)

  def test_configured(self):
    '''The staged installation links the front end under tools/.'''
    frontend = config.curry_frontend()
    self.assertTrue(os.access(frontend, os.X_OK))
    self.assertEqual(
        frontend, os.path.join(config.installed_path('tools'), 'curry-frontend')
      )
    self.assertIn(config.curry2icurry_tool(), config.CURRY2ICURRY_TOOLS)
    self.assertIn('--extended', config.frontend_flags().split())
    self.assertTrue(config.frontend_subdir())
    self.assertNotEqual(config.frontend_subdir(), config.intermediate_subdir())

  def test_command(self):
    '''The command line: --flat, the output directory, the flags, -i, name.'''
    curryfile = os.path.join(self.tmpdir, 'Sub', 'Deep.curry')
    moduledir = os.path.dirname(curryfile)
    cmd = _frontend.command(curryfile, ['/x', self.tmpdir, '/x'])
    self.assertEqual(cmd[0], config.curry_frontend())
    self.assertEqual(cmd[1:4], ['--flat', '-o', FE_SUBDIR])
    flags = config.frontend_flags().split()
    self.assertEqual(cmd[4:4 + len(flags)], flags)
    self.assertTrue(any(f.startswith('-D__PAKCS__=') for f in flags))
    dirs = cmd[4 + len(flags):-1]
    self.assertEqual(dirs[::2], ['-i'] * (len(dirs) // 2))
    self.assertEqual(
        dirs[1::2], [moduledir, '/x', self.tmpdir, config.system_curry_path()]
      )
    self.assertEqual(cmd[-1], 'Deep')
    # Quiet mode adds the options icurry uses, after the output directory.
    quiet = _frontend.command(curryfile, [], quiet=True)
    self.assertEqual(quiet[4:7], _frontend.QUIET_FLAGS)
    # The FlatCurry file lands beside the source.
    self.assertEqual(
        _frontend.flatcurryfile(curryfile)
      , os.path.join(moduledir, FE_SUBDIR, 'Deep.fcy')
      )
    # The system library is on the path when the Curry path is empty.
    self.assertEqual(
        _frontend.searchdirs(curryfile, [])
      , [moduledir, config.system_curry_path()]
      )

  def test_convert(self):
    '''The ICurry of a module is byte-identical to the file icurry wrote.'''
    self.without_cache()
    for name in ['hello', 'Peano']:
      icy = oracle_icy('', name)
      if icy is None:
        self.skipTest('%s is not in the test corpus' % name)
      curryfile = self.copy(name + '.curry')
      out = self.convert(curryfile)
      self.assertEqual(out, os.path.join(self.tmpdir, SUBDIR, name + '.icy'))
      for suffix in ['.fcy', '.fint', '.icurry']:
        self.assertTrue(os.path.isfile(
            os.path.join(self.tmpdir, FE_SUBDIR, name + suffix)
          ))
      self.assertEqual(readbytes(out), readbytes(icy))
      # The interface files travel with the ICurry: the copies beside it are
      # the files the front end wrote.
      for suffix, content in interfaces_beside(out).items():
        self.assertEqual(
            content, readbytes(_frontend.interfacefile(curryfile, suffix))
          )
        self.assertTrue(content, suffix)
      self.assertFalse(_curry2icurry.icurry_is_stale(out))
      # Again: no error, the same file.
      self.assertEqual(self.convert(curryfile, quiet=False), out)
      self.assertEqual(readbytes(out), readbytes(icy))

  def test_imports(self):
    '''The interfaces of the imports come from the same front-end run.'''
    # The test reads a file only the front end writes; a hit in the ICurry
    # cache writes the ICurry and its copies of the interfaces instead.
    self.without_cache()
    deep_icy = oracle_icy(os.path.join('flat2icurry', 'Sub'), 'Deep')
    classes_icy = oracle_icy('flat2icurry', 'Classes')
    if deep_icy is None or classes_icy is None:
      self.skipTest('the probe modules are not in the test corpus')
    deep = self.copy(os.path.join('flat2icurry', 'Sub', 'Deep.curry'))
    classes = self.copy(os.path.join('flat2icurry', 'Classes.curry'))
    root = os.path.dirname(classes)
    out = self.convert(classes, [root])
    self.assertTrue(os.path.isfile(
        os.path.join(root, FE_SUBDIR, 'Sub', 'Deep.fint')
      ))
    self.assertEqual(readbytes(out), readbytes(classes_icy))
    # Compiled by itself, the hierarchical module keeps its own directory.
    out = self.convert(deep, [root])
    self.assertEqual(out, os.path.join(root, 'Sub', SUBDIR, 'Deep.icy'))
    self.assertEqual(readbytes(out), readbytes(deep_icy))

  @cytest.with_flags(defaultconverter='topython')
  def test_typed_root(self):
    '''
    A type annotation at the root of a rule.  icurry 3.1.0 loses the bindings
    of a let or free declaration under it, and the program fails at run time.
    The route through the front end looks through the annotation, so its .icy
    differs from the oracle there and the program runs.
    '''
    curryfile = self.copy(os.path.join('flat2icurry', 'TypedRoot.curry'))
    icy = self.convert(curryfile)
    text = readbytes(icy).decode('utf-8')
    self.assertIn('(IFreeDecl 2)', text)
    # icurry's block refers to the let variable 2 without a declaration.
    self.assertNotIn(
        '(IBlock [(IVarDecl 1)] [(IVarAssign 1 (IVarAccess 0 [0]))] (IReturn (IFCall '
        '("Prelude","_impl#*#Prelude.Num#Prelude.Int",343) [(IVar 2),(IVar 2)])))'
      , text
      )
    TypedRoot = curry.import_('TypedRoot', currypath=[os.path.dirname(curryfile)])
    self.assertEqual(next(curry.eval([TypedRoot.typedLetRoot, 3])), 16)
    self.assertEqual(next(curry.eval([TypedRoot.typedFreeRoot, 3])), 3)
    self.assertEqual(sorted(curry.eval([TypedRoot.typedOrRoot, 3])), [3, 4])
    self.assertEqual(next(curry.eval([TypedRoot.typedCallRoot, 3])), 4)
    self.assertEqual(next(curry.eval([TypedRoot.typedNested, 3])), 17)

  def test_errors(self):
    '''A failure of the front end is a CompileError with its messages.'''
    curryfile = os.path.join(self.tmpdir, 'Bad.curry')
    with open(curryfile, 'w') as ostream:
      ostream.write('f=x\n')
    with self.assertRaises(exceptions.CompileError) as cm:
      self.convert(curryfile)
    message = str(cm.exception)
    self.assertIn('while running', message)
    self.assertIn(config.curry_frontend(), message)
    self.assertIn("`x' is undefined", message)
    self.assertFalse(os.path.exists(os.path.join(self.tmpdir, SUBDIR, 'Bad.icy')))
    # A missing import.
    with open(curryfile, 'w') as ostream:
      ostream.write('import NoSuchModule\n')
    with self.assertRaisesRegex(exceptions.CompileError, 'NoSuchModule'):
      self.convert(curryfile)

  def test_tool_selection(self):
    '''The tool comes from the keyword, the environment, or the configuration.'''
    self.without_cache()
    with binding.binding(os.environ, 'SPRITE_CURRY2ICURRY', 'icurry'):
      self.assertEqual(config.curry2icurry_tool(), 'icurry')
      self.assertEqual(config.curry2icurry_tool('frontend'), 'frontend')
    with binding.binding(os.environ, 'SPRITE_CURRY2ICURRY', 'bogus'):
      self.assertRaisesRegex(ValueError, 'bogus', config.curry2icurry_tool)
    with binding.binding(os.environ, 'SPRITE_CURRY2ICURRY', ''):
      self.assertEqual(
          config.curry2icurry_tool()
        , config.default_curry2icurry_tool() or 'frontend'
        )
    self.assertRaisesRegex(
        ValueError, 'bogus'
      , lambda: _curry2icurry.Curry2ICurryConverter(curry2icurry='bogus')
      )
    self.assertEqual(
        _curry2icurry.Curry2ICurryConverter(curry2icurry='frontend').tool
      , 'frontend'
      )
    converter = _curry2icurry.Curry2ICurryConverter(curry2icurry='icurry')
    self.assertEqual(converter.tool, 'icurry')
    curryfile = self.copy('hello.curry')
    if config.icurry_tool() is None:
      with self.assertRaisesRegex(exceptions.CompileError, 'icurry is not configured'):
        converter.convert(curryfile, [])
    else:
      # Both routes write the same file, and the icurry route leaves the
      # interface files of the same front end, which travel with the ICurry.
      icy = converter.convert(curryfile, [])
      text = readbytes(icy)
      interfaces = interfaces_beside(icy)
      for suffix, content in interfaces.items():
        self.assertTrue(content, suffix)
        self.assertEqual(
            content, readbytes(_frontend.interfacefile(curryfile, suffix))
          )
      os.unlink(icy)
      self.assertEqual(readbytes(self.convert(curryfile)), text)
      self.assertEqual(interfaces_beside(icy), interfaces)

  def test_stale_without_interfaces(self):
    '''
    An ICurry file without the interface files beside it is made again, with
    or without a JSON step after it; an ICurry file without a source is not.
    '''
    curryfile = self.copy('hello.curry')
    icy = self.convert(curryfile)
    full = plans.makeplan(None, plans.MAKE_ICURRY | plans.MAKE_JSON)
    icy_only = plans.makeplan(None, plans.MAKE_ICURRY)
    current = lambda plan: toolchain.currentfile(
        plan, curryfile, [], is_sourcefile=True
      )
    self.assertEqual(current(full), icy)
    self.assertEqual(current(icy_only), icy)
    fint = cache.interface_filename(icy, '.fint')
    os.unlink(fint)
    self.assertTrue(_curry2icurry.icurry_is_stale(icy))
    self.assertEqual(current(full), curryfile)
    self.assertEqual(current(icy_only), curryfile)
    # The conversion restores the file.
    self.assertEqual(self.convert(curryfile), icy)
    self.assertTrue(os.path.isfile(fint))
    self.assertEqual(current(full), icy)
    # The source is never refused, and a file that is not an ICurry file is
    # not asked about.
    self.assertFalse(_curry2icurry.icurry_is_stale(curryfile))
    self.assertFalse(_curry2icurry.icurry_is_stale(icy[:-4] + '.json'))
    # Without a source, the ICurry file stands as it is.
    os.unlink(fint)
    os.unlink(curryfile)
    self.assertFalse(_curry2icurry.icurry_is_stale(icy))
    self.assertEqual(current(full), icy)

  def test_installed_interfaces(self):
    '''
    The stage copies the interface files of every library module beside its
    installed ICurry file; the copies are the front end's files.
    '''
    root = config.system_curry_path()
    for name in config.syslibs():
      parts = name.split('.')
      icy = os.path.join(
          root, *parts[:-1], SUBDIR, parts[-1] + '.icy'
        )
      self.assertTrue(os.path.isfile(icy), icy)
      self.assertFalse(_curry2icurry.icurry_is_stale(icy), name)
      for suffix, content in interfaces_beside(icy).items():
        original = os.path.join(root, FE_SUBDIR, *parts) + suffix
        self.assertEqual(content, readbytes(original), original)
        self.assertTrue(content, original)

  def test_overlay_prune(self):
    '''
    make overlay-prune removes the extracted products of every test source
    that changed since the commit that packed the archive, and keeps the
    products of the others.  The sources come from git, so the test picks a
    changed source with products in the archive, and skips when there is
    none.
    '''
    archive = os.path.join(ROOT, 'overlay-%s.tgz' % config.frontend_subdir())
    if not os.path.isfile(archive) or not os.path.isfile(os.path.join(ROOT, 'Make.config')):
      self.skipTest('the source tree or the overlay archive is not available')
    def git(*args):
      proc = subprocess.run(
          ['git', '-C', ROOT] + list(args), stdout=subprocess.PIPE
        , stderr=subprocess.PIPE, text=True, timeout=120
        )
      return proc.stdout.split() if proc.returncode == 0 else None
    commit = git('log', '-1', '--format=%H', '--', os.path.basename(archive))
    if not commit:
      self.skipTest('no git history of the archive')
    changed = git('diff', '--name-only', commit[0], '--', 'tests/*.curry')
    self.assertIsNotNone(changed)
    changed = {os.path.relpath(name, 'tests') for name in changed}
    with tarfile.open(archive) as tar:
      members = [m for m in tar.getmembers() if m.name.startswith('tests/')]
    # The stems of the pool with products in the archive, changed and not.
    def stem(member):
      parts = member.name.split('/')
      if parts[:3] == ['tests', 'data', 'curry'] and parts[3] == '.curry' and len(parts) == 6:
        return parts[5].split('.')[0]
    stems = {stem(m) for m in members} - {None}
    stale = sorted(s for s in stems if os.path.join('data', 'curry', s + '.curry') in changed)
    kept = sorted(s for s in stems if os.path.join('data', 'curry', s + '.curry') not in changed)
    if not stale or not kept:
      self.skipTest('no changed source with products in the archive')
    chosen = [m for m in members if stem(m) in (stale[0], kept[0])]
    with tarfile.open(archive) as tar:
      tar.extractall(self.tmpdir, members=chosen, filter='data')
    def products(name):
      return sorted(
          os.path.join(dirpath, filename)
              for dirpath, _, filenames in os.walk(self.tmpdir)
              for filename in filenames if filename.split('.')[0] == name
        )
    self.assertTrue(products(stale[0]))
    self.assertTrue(products(kept[0]))
    result = subprocess.run(
        ['make', '-C', ROOT, 'overlay-prune', 'OVERLAY_ROOT=' + self.tmpdir]
      , env=MAKE_ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
      , timeout=300
      )
    self.assertEqual(result.returncode, 0, result.stdout)
    self.assertIn('rm ', result.stdout)
    self.assertEqual(products(stale[0]), [])
    self.assertTrue(products(kept[0]))

  def test_overlay_interfaces(self):
    '''
    make overlay-interfaces copies the interfaces of the front end beside
    every ICurry file of the extracted test products, so an extracted file
    whose source exists is not stale.
    '''
    archive = os.path.join(ROOT, 'overlay-%s.tgz' % config.frontend_subdir())
    if not os.path.isfile(archive) or not os.path.isfile(os.path.join(ROOT, 'Make.config')):
      self.skipTest('the source tree or the overlay archive is not available')
    prefix = 'tests/data/curry/.curry/'
    with tarfile.open(archive) as tar:
      members = [
          m for m in tar.getmembers()
            if m.name.startswith(prefix) and m.name[len(prefix):].count('/') == 1
               and os.path.basename(m.name).split('.')[0] in ('Peano', 'hello')
        ]
      self.assertTrue(members)
      tar.extractall(self.tmpdir, members=members, filter='data')
    testsdir = os.path.join(self.tmpdir, 'tests')
    icys = sorted(
        os.path.join(dirpath, name)
            for dirpath, _, names in os.walk(testsdir) for name in names
            if name.endswith('.icy')
      )
    self.assertEqual(
        [os.path.basename(icy) for icy in icys], ['Peano.icy', 'hello.icy']
      )
    for icy in icys:
      for suffix in cache.INTERFACE_SUFFIXES:
        self.assertFalse(os.path.exists(cache.interface_filename(icy, suffix)))
    # With a source beside them, the extracted files are stale until the
    # copies exist.
    with open(os.path.join(testsdir, 'data', 'curry', 'Peano.curry'), 'w'):
      pass
    peano = os.path.join(testsdir, 'data', 'curry', SUBDIR, 'Peano.icy')
    self.assertTrue(_curry2icurry.icurry_is_stale(peano))
    result = subprocess.run(
        ['make', '-C', ROOT, 'overlay-interfaces', 'OVERLAY_DIR=' + testsdir]
      , env=MAKE_ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
      , timeout=300
      )
    self.assertEqual(result.returncode, 0, result.stdout)
    self.assertFalse(_curry2icurry.icurry_is_stale(peano))
    for icy in icys:
      stem = os.path.basename(icy)[:-len('.icy')]
      for suffix, content in interfaces_beside(icy).items():
        original = os.path.join(testsdir, 'data', 'curry', FE_SUBDIR, stem + suffix)
        self.assertEqual(content, readbytes(original), original)
        self.assertTrue(content, original)
    # The copies are the only new files.
    names = sorted(
        name for _, _, names in os.walk(os.path.join(testsdir, 'data', 'curry', SUBDIR))
             for name in names
      )
    self.assertEqual(
        names
      , [ 'Peano.fint', 'Peano.icurry', 'Peano.icy', 'Peano.json.z'
        , 'hello.fint', 'hello.icurry', 'hello.icy', 'hello.json.z'
        ]
      )

  def test_sprite_make(self):
    '''sprite-make selects the tool with --curry2icurry.'''
    makeprg = os.path.join(os.environ['SPRITE_HOME'], 'bin', 'sprite-make')
    curryfile = self.copy('hello.curry')
    icy = os.path.join(self.tmpdir, SUBDIR, 'hello.icy')
    subprocess.check_output([makeprg, '--icy', '--curry2icurry', 'frontend', curryfile])
    self.assertTrue(os.path.isfile(icy))
    oracle = oracle_icy('', 'hello')
    if oracle is not None:
      self.assertEqual(readbytes(icy), readbytes(oracle))
    with self.assertRaises(subprocess.CalledProcessError):
      subprocess.check_output(
          [makeprg, '--icy', '--curry2icurry', 'bogus', curryfile]
        , stderr=subprocess.DEVNULL
        )
    usage = subprocess.check_output([makeprg, '-h']).decode('utf-8')
    self.assertIn('--curry2icurry', usage)

import cytest # from ./lib; must be first
from curry import cache, config, exceptions, toolchain
from curry.toolchain import _curry2icurry, _frontend, plans
from curry.utility import binding
import flat2icurry_oracle as oracle
import curry, os, shutil, subprocess, tarfile, tempfile, time, unittest
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
    with mock.patch.dict(os.environ, {_frontend.WARNINGS_VARIABLE: '1'}):
      cmd = _frontend.command(curryfile, ['/x', self.tmpdir, '/x'])
    self.assertEqual(cmd[0], config.curry_frontend())
    self.assertEqual(cmd[1:4], ['--flat', '-o', FE_SUBDIR])
    # A run that reports adds the options of the warning on overlapping
    # rules alone, after the output directory (issue #96).
    warn = _frontend.WARNING_FLAGS
    self.assertEqual(cmd[4:4 + len(warn)], warn)
    flags = config.frontend_flags().split()
    start = 4 + len(warn)
    self.assertEqual(cmd[start:start + len(flags)], flags)
    self.assertTrue(any(f.startswith('-D__PAKCS__=') for f in flags))
    dirs = cmd[start + len(flags):-1]
    self.assertEqual(dirs[::2], ['-i'] * (len(dirs) // 2))
    self.assertEqual(
        dirs[1::2], [moduledir, '/x', self.tmpdir, config.system_curry_path()]
      )
    self.assertEqual(cmd[-1], 'Deep')
    # Quiet mode adds the options icurry uses, after the output directory.
    quiet = _frontend.command(curryfile, [], quiet=True)
    self.assertEqual(quiet[4:7], _frontend.QUIET_FLAGS)
    # SPRITE_FRONTEND_WARNINGS=0 makes every command quiet; the test
    # library sets it for the suite.
    with mock.patch.dict(os.environ, {_frontend.WARNINGS_VARIABLE: '0'}):
      self.assertFalse(_frontend.frontend_warnings())
      self.assertEqual(_frontend.command(curryfile, [])[4:7], _frontend.QUIET_FLAGS)
    for value in '1', 'on', '':
      with mock.patch.dict(os.environ, {_frontend.WARNINGS_VARIABLE: value}):
        self.assertTrue(_frontend.frontend_warnings(), repr(value))
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
    # Both routes need the front end: the icurry route runs it first and
    # rewrites its FlatCurry file.  The messages name the real requirement
    # before any program runs.
    icyfile = os.path.join(self.tmpdir, 'hello.icy')
    with mock.patch.object(config, 'curry_frontend', return_value=None):
      with self.assertRaisesRegex(
          exceptions.CompileError, 'not configured; rerun configure with --with-curry-frontend'
        ):
        _frontend.command(curryfile, [])
      with mock.patch.object(config, 'icurry_tool', return_value='/no/such/icurry'):
        with self.assertRaisesRegex(
            exceptions.CompileError, 'the icurry route needs the Curry front end as well'
          ):
          converter.command(curryfile, icyfile, [])
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

  def test_binding_optimization(self):
    '''
    The route rewrites the FlatCurry file of the module in place before the
    translation (the binding optimization of PAKCS): the file on disk is the
    optimized program, the ICurry is its plain translation, and the oracle
    harness finds the two equal.  A second conversion changes neither.
    '''
    self.without_cache()
    curryfile = self.copy('sendMoreMoney.curry')
    icy = self.convert(curryfile)
    fcy = _frontend.flatcurryfile(curryfile)
    fcytext, icytext = readbytes(fcy), readbytes(icy)
    self.assertTrue(fcytext.startswith(b'Prog "sendMoreMoney" '))
    self.assertEqual(fcytext.count(b'constrEq'), 15)
    self.assertNotIn(b'_impl#==#', fcytext)
    self.assertEqual(icytext.count(b'constrEq'), 15)
    result = oracle.check_file(fcy, icyfile=icy)
    self.assertEqual(result.status, oracle.EQUAL, result.detail)
    mtime = os.stat(fcy).st_mtime_ns
    self.assertEqual(self.convert(curryfile), icy)
    self.assertEqual(os.stat(fcy).st_mtime_ns, mtime)
    self.assertEqual(readbytes(icy), icytext)
    # A module in which nothing is replaced keeps the bytes of the front end.
    hello = self.copy('hello.curry')
    other = os.path.join(self.tmpdir, 'other', 'hello.curry')
    os.makedirs(os.path.dirname(other))
    shutil.copy(hello, other)
    self.convert(hello)
    self.assertEqual(
        readbytes(_frontend.flatcurryfile(hello))
      , readbytes(_frontend.curry2flat(other, [], quiet=True))
      )

  def test_binding_optimization_icurry(self):
    '''
    The icurry route runs the front end and the rewrite first, so the icurry
    program reads the optimized file and writes the same ICurry as the route
    through the port.
    '''
    if config.icurry_tool() is None:
      self.skipTest('icurry is not configured')
    self.without_cache()
    port = readbytes(self.convert(self.copy('sendMoreMoney.curry')))
    other = os.path.join(self.tmpdir, 'other', 'sendMoreMoney.curry')
    os.makedirs(os.path.dirname(other))
    shutil.copy(os.path.join(DATA, 'sendMoreMoney.curry'), other)
    icy = self.convert(other, curry2icurry='icurry')
    self.assertEqual(readbytes(icy), port)
    self.assertEqual(readbytes(_frontend.flatcurryfile(other)).count(b'constrEq'), 15)
    self.assertFalse(_curry2icurry.icurry_is_stale(icy))

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
    self.assertIn('--rewrite-flat', usage)

  def test_sprite_make_rewrite_flat(self):
    '''
    sprite-make --rewrite-flat runs the step from Curry to ICurry again,
    current or not: a FlatCurry file written before the routes rewrote it
    gets the pass, and the ICurry is made from it.
    '''
    makeprg = os.path.join(os.environ['SPRITE_HOME'], 'bin', 'sprite-make')
    # The children run without the ICurry cache: a hit writes no FlatCurry.
    env = dict(os.environ, SPRITE_CACHE_FILE='')
    def make(*args):
      return subprocess.run(
          [makeprg] + list(args), env=env, stdout=subprocess.PIPE
        , stderr=subprocess.PIPE, text=True, timeout=300
        )
    curryfile = self.copy('sendMoreMoney.curry')
    fcy = _frontend.flatcurryfile(curryfile)
    icy = os.path.join(self.tmpdir, SUBDIR, 'sendMoreMoney.icy')
    self.assertEqual(make('--icy', curryfile).returncode, 0)
    optimized, icytext = readbytes(fcy), readbytes(icy)
    self.assertIn(b'constrEq', optimized)
    # The front end's text takes the place of the file, as a product of an
    # older toolchain would be.  A plain run finds the module current and
    # leaves it; --rewrite-flat rewrites the file and the ICurry.
    older = os.path.join(self.tmpdir, 'older', 'sendMoreMoney.curry')
    os.makedirs(os.path.dirname(older))
    shutil.copy(curryfile, older)
    unoptimized = readbytes(
        _frontend.curry2flat(older, [], quiet=True, rewrite=False)
      )
    self.assertNotIn(b'constrEq', unoptimized)
    with open(fcy, 'wb') as ostream:
      ostream.write(unoptimized)
    mtime = os.stat(icy).st_mtime_ns
    self.assertEqual(make('--icy', curryfile).returncode, 0)
    self.assertEqual(readbytes(fcy), unoptimized)
    self.assertEqual(os.stat(icy).st_mtime_ns, mtime)
    proc = make('--rewrite-flat', '--json', curryfile)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(readbytes(fcy), optimized)
    self.assertEqual(readbytes(icy), icytext)
    self.assertGreater(os.stat(icy).st_mtime_ns, mtime)
    self.assertTrue(os.path.isfile(icy[:-4] + '.json'))
    # The option stands alone: it is the step from Curry to ICurry (#99).
    with open(fcy, 'wb') as ostream:
      ostream.write(unoptimized)
    mtime = os.stat(icy).st_mtime_ns
    proc = make('--rewrite-flat', curryfile)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(readbytes(fcy), optimized)
    self.assertEqual(readbytes(icy), icytext)
    self.assertGreater(os.stat(icy).st_mtime_ns, mtime)
    # The option runs the modules in this process, and needs the source.
    proc = make('--rewrite-flat', '--icy', '--jobs', '2', curryfile)
    self.assertEqual(proc.returncode, 1)
    self.assertIn('--jobs 1', proc.stderr)
    os.unlink(curryfile)
    proc = make('--rewrite-flat', '--icy', curryfile)
    self.assertEqual(proc.returncode, 1)
    self.assertIn('needs the Curry source', proc.stderr)

  def test_import_compiled_again_is_rewritten(self):
    '''
    A run of the front end on a module compiles an import again when the
    interface of the import is older than the interface of one of its own
    imports, and writes the FlatCurry of the import in its own text.  The
    route rewrites every FlatCurry file the run wrote, so the file of the
    import keeps the pass and pairs with the ICurry beside it (issue #99).
    '''
    self.without_cache()
    def write(name, text):
      path = os.path.join(self.tmpdir, name + '.curry')
      with open(path, 'w', encoding='utf-8') as ostream:
        ostream.write(text)
      return path
    write('ImpC', 'module ImpC where\nc :: Int\nc = 1\n')
    impb = write(
        'ImpB', 'module ImpB where\nimport ImpC\nf :: Int -> Int\nf x | x == c = x\n'
      )
    impa = write('ImpA', 'module ImpA where\nimport ImpB\nmain :: Int\nmain = f 1\n')
    icy_b = self.convert(impb, [self.tmpdir])
    fcy_b = _frontend.flatcurryfile(impb)
    rewritten = readbytes(fcy_b)
    self.assertEqual(rewritten.count(b'constrEq'), 1)
    # The interface of ImpC gets a newer time than the interface of ImpB:
    # the front end then compiles ImpB again in the run on ImpA.
    time.sleep(0.01)
    os.utime(_frontend.interfacefile(os.path.join(self.tmpdir, 'ImpC.curry'), '.icurry'))
    stamp = os.stat(fcy_b).st_mtime_ns
    self.convert(impa, [self.tmpdir])
    self.assertNotEqual(os.stat(fcy_b).st_mtime_ns, stamp, 'the front end did not compile ImpB again')
    self.assertEqual(readbytes(fcy_b), rewritten)
    result = oracle.check_file(fcy_b, [self.tmpdir], icyfile=icy_b)
    self.assertEqual(result.status, oracle.EQUAL, result.detail)
    # Without the rewrite the run leaves the text of the front end.
    os.utime(_frontend.interfacefile(os.path.join(self.tmpdir, 'ImpC.curry'), '.icurry'))
    _frontend.curry2flat(impa, [self.tmpdir], quiet=True, rewrite=False)
    self.assertNotIn(b'constrEq', readbytes(fcy_b))
    self.assertEqual(
        oracle.check_file(fcy_b, [self.tmpdir], icyfile=icy_b).status
      , oracle.DIFFERENT
      )
    # The rewrite reaches the directories of the Curry path, not the
    # system library (flatcurry_dirs).
    dirs = _frontend.flatcurry_dirs(impa, [self.tmpdir, config.system_curry_path()])
    self.assertEqual(dirs, [os.path.join(self.tmpdir, FE_SUBDIR)])

# The modules of TestDeepExpressions (issue #125): a literal list of
# ELEMENTS elements, and a chain of ELEMENTS applications of a binary
# operator.  The case on a literal is a Boolean equality in FlatCurry, so
# the binding optimization rebuilds the body of g.
ELEMENTS = 1200

LONG_LIST_TEMPLATE = '''e :: Int -> Int
e i = i ? (i + 1)

g :: Int -> [Int]
g n = case n of { 1 -> [%s]; _ -> [] }

longHead :: Int
longHead = head (g (length [()]))
'''

def long_list(elements):
  '''The module of a literal list of ``elements`` elements.'''
  return LONG_LIST_TEMPLATE % ', '.join(
      'e %d' % i for i in range(1, elements + 1)
    )

LONG_LIST = long_list(ELEMENTS)

DEEP_SUM = '''e :: Int -> Int
e i = i ? (i + 1)

g :: Int -> Int
g n = case n of { 1 -> %s; _ -> 0 }

deepHead :: Int
deepHead = g (length [()])
''' % ('0 + (' * ELEMENTS + 'e 1' + ')' * ELEMENTS)

class TestDeepExpressions(cytest.TestCase):
  '''
  A module with a deeply nested expression imports and runs on both
  backends (issue #125).  The port of icurry recursed once per element of
  a literal list, first in the binding optimization, then in the passes
  after it and in the reader of the ICurry text; the Python backend wrote
  the expression as one nested call, which the parser of Python refuses
  past 200 parentheses; the interpreter of the C++ runtime recursed in its
  emitter.  The module is written by the test, as the script of the issue
  does, and the ICurry cache is off, so the route runs every time.  The
  tests run under interpret:new: they pin the import, the emitters and the
  evaluation, not the compile with g++ (about 18 s and 800 MB of resident
  memory per module in a background child under the tiered default).
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
    patcher = mock.patch.dict(os.environ, {'SPRITE_CACHE_FILE': ''})
    patcher.start()
    self.addCleanup(patcher.stop)
    cache.reset()
    self.addCleanup(cache.reset)

  def values(self, name, text, goal):
    '''Writes the module, imports it, and evaluates the goal.'''
    curryfile = os.path.join(self.tmpdir, name + '.curry')
    with open(curryfile, 'w', encoding='utf-8') as ostream:
      ostream.write(text)
    M = curry.import_(name, currypath=[self.tmpdir])
    return list(curry.eval(getattr(M, goal), converter='topython'))

  @cytest.with_flags(interpret='new')
  def test_long_literal_list(self):
    self.assertEqual(self.values('LongList', LONG_LIST, 'longHead'), [1, 2])

  @cytest.with_flags(interpret='new')
  def test_nested_operator(self):
    self.assertEqual(self.values('DeepSum', DEEP_SUM, 'deepHead'), [1, 2])

  # The bounds left after the fix of the walks of the port (the entry of
  # 2026-10-09 in the TODO), each pinned at twice its old bound: the copy
  # of a function body in the inliner failed at about 2700 elements (six
  # frames per element through copy.deepcopy), the expression compiler of
  # both backends at about 4000 (four frames per element), and the visitor
  # of the optimizer at about 5400 (three).  One import runs all three
  # walks, so each test is the import at its size (pothole batch 4,
  # 2026-10-10).

  @cytest.with_flags(interpret='new')
  def test_inliner_copy_bound(self):
    self.assertEqual(
        self.values('LongList5400', long_list(5400), 'longHead'), [1, 2]
      )

  @cytest.with_flags(interpret='new')
  def test_expression_compiler_bound(self):
    self.assertEqual(
        self.values('LongList8000', long_list(8000), 'longHead'), [1, 2]
      )

  @cytest.with_flags(interpret='new')
  def test_visitor_bound(self):
    self.assertEqual(
        self.values('LongList10800', long_list(10800), 'longHead'), [1, 2]
      )

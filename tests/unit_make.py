import cytest # from ./lib; must be first
import curry
from curry import config, icurry, interpreter, toolchain
from curry.interpreter import flags as _flags
from curry.toolchain import plans
from curry.tools import make
from curry.toolchain import _productlock, _system
from curry.utility.binding import binding
from curry.utility.strings import ensure_str
from unittest import mock
import argparse, contextlib, errno, fcntl, glob, io, itertools, json, os
import shutil, subprocess, sys, tempfile, threading, time, unittest, zlib

SUBDIR = os.path.join('.curry', config.intermediate_subdir())

class TestMake(cytest.TestCase):
  '''Tests for the make-like features to generate ICurry and JSON.'''

  def test_filename_funcs(self):
    '''Checks derivation of intermediate file names.'''
    prefixes = ['', '/path/to', 'a/b', '.', '..']
    for prefix in prefixes:
      curry_file = os.path.join(prefix, 'foo.curry')
      icy_file   = os.path.join(prefix, SUBDIR, 'foo.icy')
      json_file  = os.path.join(prefix, SUBDIR, 'foo.json')
      jsonz_file = os.path.join(prefix, SUBDIR, 'foo.json.z')
      py_file    = os.path.join(prefix, SUBDIR, 'foo.py')
      cpp_file   = os.path.join(prefix, SUBDIR, 'foo.cpp')
      so_file    = os.path.join(prefix, SUBDIR, 'foo.so')
      files = [
          curry_file, icy_file, json_file, jsonz_file, py_file, cpp_file, so_file
        ]
      json_files = [json_file, jsonz_file]
      for file_ in files:
        self.assertEqual(toolchain.curryfilename(file_), curry_file)
        self.assertEqual(toolchain.icurryfilename(file_), icy_file)
        self.assertEqual(set(toolchain.jsonfilenames(file_)), set(json_files))

  def test_make_icurry_and_json(self):
    '''Test the conversion from .curry to .icy.'''
    for input_file in glob.glob('data/importer/*.curry'):
      dirname, filename = os.path.split(input_file)
      stem = filename[:-6]
      with tempfile.TemporaryDirectory() as tmpdir:
        shutil.copy(input_file, tmpdir)
        curry_file = os.path.join(tmpdir, filename)
        # Build .icy.
        ret = toolchain.curry2icurry(curry_file, currypath=[], quiet=True)
        file_out = os.path.join(tmpdir, SUBDIR, stem + '.icy')
        self.assertTrue(os.path.exists(file_out))
        self.assertEqual(ret, file_out)
        # Repeat -- no exception.
        ret = toolchain.curry2icurry(curry_file, currypath=[], quiet=True)
        self.assertEqual(ret, file_out)

        # Build .json.
        ret = toolchain.icurry2json(curry_file, currypath=[], compact=False, zip=False)
        json_file = os.path.join(tmpdir, SUBDIR, stem + '.json')
        self.assertTrue(os.path.exists(json_file))
        self.assertEqual(ret, json_file)
        shutil.move(json_file, json_file + '.nocompact')

        # Build compacted .json.
        self.assertFalse(os.path.exists(json_file))
        ret = toolchain.icurry2json(curry_file, currypath=[], compact=True, zip=False)
        self.assertTrue(os.path.exists(json_file))
        self.assertEqual(ret, json_file)
        self.assertLess(
            os.stat(json_file).st_size
          , os.stat(json_file + '.nocompact').st_size
          )
        # Both forms end with a newline and decode to the same module.  The
        # compact form is the text of the encoder.
        compact = cytest.readfile(json_file)
        spaced = cytest.readfile(json_file + '.nocompact')
        self.assertTrue(compact.endswith('}\n'))
        self.assertTrue(spaced.endswith('}\n'))
        self.assertIn('": ', spaced)
        self.assertEqual(icurry.json.loads(compact), icurry.json.loads(spaced))
        self.assertEqual(
            compact, icurry.json.dumps(icurry.readcurry.load(file_out)) + '\n'
          )
        shutil.move(json_file, json_file + '.nozip')

        # Build compacted, compressed .json.
        ret = toolchain.icurry2json(curry_file, currypath=[], compact=True, zip=True)
        self.assertTrue(os.path.exists(json_file + '.z'))
        self.assertEqual(ret, json_file + '.z')
        self.assertLess(
            os.stat(json_file + '.z').st_size
          , os.stat(json_file + '.nozip').st_size
          )

  def test_makecurry(self):
    '''Test the makecurry function.'''
    for input_file in glob.glob('data/importer/*.curry'):
      dirname, filename = os.path.split(input_file)
      stem = filename[:-6]
      plan_icy = plans.makeplan(
          curry.getInterpreter(), plans.MAKE_ICURRY
        )
      plan_json = plans.makeplan(
          curry.getInterpreter(), plans.MAKE_ICURRY | plans.MAKE_JSON
        )
      with tempfile.TemporaryDirectory() as tmpdir:
        shutil.copy(input_file, tmpdir)
        icy_file = os.path.join(tmpdir, SUBDIR, stem + '.icy')
        json_file = os.path.join(tmpdir, SUBDIR, stem + '.json')
        curry_file = os.path.join(tmpdir, filename)
        # Make .icy.
        ret = toolchain.makecurry(plan_icy, curry_file, is_sourcefile=True)
        self.assertTrue(os.path.exists(icy_file))
        self.assertTrue(ret.endswith('.icy'))
        # Repeat
        ret = toolchain.makecurry(plan_icy, curry_file, is_sourcefile=True)
        self.assertTrue(os.path.exists(icy_file))
        self.assertTrue(ret.endswith('.icy'))

        # Make .json.  Returns the JSON file name.
        ret = toolchain.makecurry(plan_json, curry_file, is_sourcefile=True)
        self.assertTrue(os.path.exists(json_file))
        self.assertEqual(ret, json_file)
        # Repeat
        ret = toolchain.makecurry(plan_json, curry_file, is_sourcefile=True)
        self.assertTrue(os.path.exists(json_file))
        self.assertEqual(ret, json_file)

  def test_sprite_make_icy(self):
    '''
    Test the conversion of a committed ICurry file to JSON.  The Curry library
    ships its ICurry files beside the sources, and make derives the JSON from
    them without icurry.
    '''
    from curry import icurry
    makeprg = os.path.join(os.environ['SPRITE_HOME'], 'bin', 'sprite-make')
    def sprite_make(*args):
      return ensure_str(subprocess.check_output((makeprg,) + args))
    icy_src = os.path.join('data', 'curry', SUBDIR, 'hello.icy')
    with tempfile.TemporaryDirectory() as tmpdir:
      icy_file = os.path.join(tmpdir, 'hello.icy')
      shutil.copy(icy_src, icy_file)
      sprite_make('--json', '-zc', icy_file)
      jsonz_file = os.path.join(tmpdir, 'hello.json.z')
      self.assertTrue(os.path.exists(jsonz_file))
      with open(jsonz_file, 'rb') as istream:
        import zlib
        imodule = icurry.json.loads(zlib.decompress(istream.read()))
      self.assertEqual(imodule, icurry.readcurry.load(icy_file))
      # The output option copies the JSON.
      copy = os.path.join(tmpdir, 'copy.json.z')
      sprite_make('--json', '-zc', '-o', copy, icy_file)
      with open(copy, 'rb') as a, open(jsonz_file, 'rb') as b:
        self.assertEqual(a.read(), b.read())
      # Only JSON can be made from an ICurry file.
      with self.assertRaises(subprocess.CalledProcessError):
        subprocess.check_output(
            [makeprg, '--icy', icy_file], stderr=subprocess.DEVNULL
          )

  def test_sprite_make(self):
    '''Test the sprite-make program.'''
    makeprg = os.path.join(os.environ['SPRITE_HOME'], 'bin', 'sprite-make')
    def sprite_make(*args):
      return ensure_str(subprocess.check_output((makeprg,) + args))

    self.assertEqual(sprite_make('--subdir'), SUBDIR)
    self.assertEqual(sprite_make('-S'), SUBDIR)

    maninfo = sprite_make('--man')
    self.assertEqual(sprite_make('-M'), maninfo)
    self.assertGreater(len(maninfo), 100)
    self.assertIn('Examples', maninfo)
    self.assertIn('CURRYPATH', maninfo)
    self.assertIn('SPRITE_LOG_LEVEL', maninfo)

    for input_file in glob.glob('data/importer/*.curry'):
      dirname, filename = os.path.split(input_file)
      stem = filename[:-6]
      with tempfile.TemporaryDirectory() as tmpdir:
        shutil.copy(input_file, tmpdir)
        curry_file = os.path.join(tmpdir, filename)
        icy_file = os.path.join(tmpdir, SUBDIR, stem + '.icy')
        json_file = os.path.join(tmpdir, SUBDIR, stem + '.json')

        # Make .json and remove .icy.
        sprite_make('--json', '-t', curry_file)
        self.assertFalse(os.path.exists(icy_file))
        self.assertTrue(os.path.exists(json_file))
        os.unlink(json_file)

        # Make .icy.
        sprite_make('--icy', curry_file)
        self.assertTrue(os.path.exists(icy_file))
        self.assertFalse(os.path.exists(json_file))

        # Make .json and keep .icy.
        sprite_make('--json', curry_file)
        self.assertTrue(os.path.exists(icy_file))
        self.assertTrue(os.path.exists(json_file))

        # Make .json.z.  Tidy will not remove the .icy.
        sprite_make('--json', '-zt', curry_file)
        self.assertTrue(os.path.exists(icy_file))
        self.assertTrue(os.path.exists(json_file + '.z'))
        os.unlink(icy_file)
        os.unlink(json_file)
        shutil.move(json_file + '.z', json_file + '.z.nocompact')

        # Make .json.z with all options.
        sprite_make('--json', '-czt', curry_file)
        self.assertFalse(os.path.exists(icy_file))
        self.assertFalse(os.path.exists(json_file))
        self.assertTrue(os.path.exists(json_file + '.z'))
        self.assertLess(
            os.stat(json_file + '.z').st_size
          , os.stat(json_file + '.z.nocompact').st_size
          )

  def test_sprite_make_so(self):
    '''
    --so runs the plan of the C++ backend to the shared object, and implies
    --cxx.  A second run compiles nothing.  --so and --py exclude each other.
    The module comes from hand-written ICurry-JSON, so no front end runs.
    '''
    if config.cxx_tool() is None:
      self.skipTest('no C++ compiler is installed')
    name = 'MakeSoTest'
    with tempfile.TemporaryDirectory() as tmpdir:
      subdir = os.path.join(tmpdir, SUBDIR)
      os.makedirs(subdir)
      with open(os.path.join(subdir, name + '.json.z'), 'wb') as stream:
        stream.write(zlib.compress(cytest.json_module(name, 5).encode('utf-8')))
      with binding(os.environ, 'CURRYPATH', tmpdir):
        make.main('sprite-make', ['--so', '-z', name])
        for suffix in ['.cpp', '.so', '.so.abi']:
          self.assertTrue(
              os.path.isfile(os.path.join(subdir, name + suffix)), suffix
            )
        # The object is current, so the second run calls no compiler.
        with mock.patch.object(
            _system, 'pexec', side_effect=AssertionError('a compiler ran')
          ):
          make.main('sprite-make', ['--so', '-z', name])
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
          with self.assertRaises(SystemExit):
            make.main('sprite-make', ['--so', '--py', name])
        self.assertIn('at most one of', stderr.getvalue())

class TestJobs(cytest.TestCase):
  '''
  The --jobs option: the modules are made by child processes, the imports of
  a module before the module, and a module whose files are current gets no
  child.  The modules come from hand-written ICurry-JSON, so no Curry front
  end runs.  The target is the one of the backend under test.
  '''
  # The C++ runtime keeps one entry per module name, so every module built in
  # this process gets a new name.
  counter = itertools.count()

  def setUp(self):
    super().setUp()
    if curry.flags['backend'] == 'cxx' and config.cxx_tool() is None:
      self.skipTest('no C++ compiler is installed')
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-jobs-')
    self.addCleanup(shutil.rmtree, self.tmpdir, True)
    self.subdir = os.path.join(self.tmpdir, SUBDIR)
    os.makedirs(self.subdir)
    self.target = '--py' if curry.flags['backend'] == 'py' else '--so'
    self.suffix = curry.getInterpreter().backend.object_file_extension
    # The plan of sprite-make: an explicit compile compiles, so its
    # interpreter has the flag ``interpret`` off (make.main).  Under the
    # tiered default of the C++ backend the plan of an import ends at the
    # JSON, and a module made here, which has its JSON alone, would count as
    # current.
    self.plan = plans.makeplan(
        interpreter.Interpreter(
            flags=_flags.getflags(
                {'backend': curry.flags['backend'], 'interpret': 'off'}
              )
          )
      , plans.MAKE_ALL | plans.ZIP_JSON
      )

  def new_name(self):
    return 'JobsTest%d' % next(self.counter)

  def write_module(self, value, imports=(), name=None, text=None):
    '''
    Writes the JSON of a module whose goal returns ``value`` and that imports
    the named modules after the Prelude.  ``text`` replaces the JSON (an
    unreadable file, say).  Returns the module name.
    '''
    if name is None:
      name = self.new_name()
    if text is None:
      text = cytest.json_module(name, value).replace(
          '"imports":["Prelude"]'
        , '"imports":%s' % json.dumps(['Prelude'] + list(imports))
        )
    with open(os.path.join(self.subdir, name + '.json.z'), 'wb') as stream:
      stream.write(zlib.compress(text.encode('utf-8')))
    return name

  def product(self, name):
    return os.path.join(self.subdir, name + self.suffix)

  @contextlib.contextmanager
  def currypath(self):
    '''Binds CURRYPATH to the temporary directory, for this process and its children.'''
    try:
      with binding(os.environ, 'CURRYPATH', self.tmpdir):
        config.currypath(reset=True)
        yield
    finally:
      config.currypath(reset=True)

  def sprite_make(self, *args):
    '''
    Runs sprite-make in this process and returns the commands of the
    children it started, in the order they started.
    '''
    module = config.python_package_name() + '.tools.make'
    with self.currypath():
      with mock.patch.object(subprocess, 'Popen', wraps=subprocess.Popen) as popen:
        make.main('sprite-make', list(args))
    return [
        call.args[0] for call in popen.call_args_list
                     if call.args[0][1:3] == ['-m', module]
      ]

  def test_jobs_option(self):
    '''--jobs takes a positive count or auto.'''
    self.assertEqual(make.parse_jobs('1'), 1)
    self.assertEqual(make.parse_jobs('12'), 12)
    self.assertEqual(make.parse_jobs('auto'), os.process_cpu_count())
    for text in ['0', '-2', 'x', '']:
      self.assertIsNone(make.parse_jobs(text), text)
    with contextlib.redirect_stderr(io.StringIO()) as stderr:
      with self.assertRaises(SystemExit) as cm:
        make.main('sprite-make', ['--json', '--jobs', '0', 'Prelude'])
    self.assertEqual(cm.exception.code, 1)
    self.assertIn('--jobs should be a count or auto', stderr.getvalue())
    man = ensure_str(subprocess.check_output([
        os.path.join(os.environ['SPRITE_HOME'], 'bin', 'sprite-make'), '--man'
      ]))
    self.assertIn('--jobs', man)
    # The order covers the files this program writes; the interface files
    # of the front end are named as the exception.
    self.assertIn('interface files of the Curry front end', man)
    self.assertIn('--jobs 1', man)

  def test_child_command(self):
    '''A child runs this program on one module with the options of the parent, less --jobs.'''
    args = argparse.Namespace(
        compact=True, cxx=True, so=True, icy=True, json=True, keep_going=True
      , py=False, quiet=True, tidy=False, zip=True, curry2icurry='frontend'
      , goal=None
      )
    cmd = make.child_command(args, make.Job('Data.Maybe', '/x/Data/Maybe.curry'))
    self.assertEqual(
        cmd[:3], [sys.executable, '-m', config.python_package_name() + '.tools.make']
      )
    self.assertEqual(cmd[-1], 'Data.Maybe')
    for flag in [ '--compact', '--cxx', '--so', '--icy', '--json', '--keep-going'
                , '--quiet', '--zip' ]:
      self.assertIn(flag, cmd)
    for flag in ['--tidy', '--py', '--jobs', '--goal']:
      self.assertNotIn(flag, cmd)
    self.assertEqual(cmd[cmd.index('--curry2icurry') + 1], 'frontend')
    args.goal = 'main'
    args.curry2icurry = None
    cmd = make.child_command(args, make.Job('A', '/x/A.curry'))
    self.assertEqual(cmd[cmd.index('--goal') + 1], 'main')
    self.assertNotIn('--curry2icurry', cmd)
    # The child finds this package first.
    env = make.child_environment()
    root = os.path.dirname(os.path.dirname(os.path.abspath(curry.__file__)))
    self.assertEqual(env['PYTHONPATH'].split(os.pathsep)[0], root)

  def test_imports_of(self):
    '''
    The imports of a module come from its source, with the implicit Prelude,
    else from its JSON file; an unreadable or missing file gives none.
    '''
    src = os.path.join(self.tmpdir, 'Src.curry')
    with open(src, 'w') as stream:
      stream.write(
          'module Src where\nimport Data.Maybe\nimport qualified Data.List as L\n'
          '-- import Not.Here\nmain = 1\n'
        )
    # The scan is lenient (see curry.cache): a declaration in a comment counts.
    self.assertEqual(
        make.imports_of(src), ['Prelude', 'Data.Maybe', 'Data.List', 'Not.Here']
      )
    prelude = os.path.join(self.tmpdir, 'Prelude.curry')
    with open(prelude, 'w') as stream:
      stream.write('module Prelude where\n')
    self.assertEqual(make.imports_of(prelude), [])
    name = self.write_module(1, imports=['Data.Char'])
    self.assertEqual(
        make.imports_of(os.path.join(self.tmpdir, name + '.curry'))
      , ['Prelude', 'Data.Char']
      )
    name = self.write_module(0, text='not a module')
    self.assertEqual(make.imports_of(os.path.join(self.tmpdir, name + '.curry')), [])
    self.assertEqual(make.imports_of(os.path.join(self.tmpdir, 'Missing.curry')), [])

  def test_graph(self):
    '''
    The job graph holds the stale modules of the closure, a module after its
    imports; a current module adds no job but passes the jobs of its imports
    on; a cycle adds no edge.
    '''
    c = self.write_module(1)
    b = self.write_module(2, imports=[c])
    a = self.write_module(3, imports=[b, c])
    currypath = [self.tmpdir] + curry.path
    graph = make.JobGraph(self.plan, currypath)
    job, currentfile = graph.add(a)
    self.assertEqual(job.arg, a)
    self.assertEqual(currentfile, os.path.join(self.subdir, a + '.json.z'))
    self.assertEqual([j.arg for j in graph.jobs], [c, b, a])
    jobs = {j.arg: j for j in graph.jobs}
    self.assertEqual(jobs[c].imports, [])
    self.assertEqual(jobs[b].imports, [jobs[c]])
    self.assertEqual(jobs[a].imports, [jobs[b], jobs[c]])
    # The Prelude is current, so the closure of a module that imports it alone
    # is the module itself.  A second add of a visited module adds nothing.
    self.assertEqual(graph.add(c), (jobs[c], os.path.join(self.subdir, c + '.json.z')))
    self.assertEqual(len(graph.jobs), 3)
    # The Prelude of the installation is current: no job, and no edge.
    graph = make.JobGraph(self.plan, currypath)
    self.assertEqual(graph.add('Prelude')[0], None)
    self.assertEqual(graph.jobs, [])
    # A cycle.
    p, q = self.new_name(), self.new_name()
    self.write_module(4, imports=[q], name=p)
    self.write_module(5, imports=[p], name=q)
    graph = make.JobGraph(self.plan, currypath)
    graph.add(p)
    self.assertEqual([j.arg for j in graph.jobs], [q, p])
    self.assertEqual(graph.jobs[0].imports, [])
    self.assertEqual(graph.jobs[1].imports, [graph.jobs[0]])

  def test_imports_are_made_first(self):
    '''
    One child per stale module of the closure, a module after its imports,
    although only the top module is named.  A second run finds every file
    current and starts no child.
    '''
    c = self.write_module(1)
    b = self.write_module(2, imports=[c])
    a = self.write_module(3, imports=[b, c])
    commands = self.sprite_make(self.target, '-z', '-c', '--jobs', '3', a)
    self.assertEqual([cmd[-1] for cmd in commands], [c, b, a])
    for cmd in commands:
      self.assertIn(self.target, cmd)
      self.assertIn('--zip', cmd)
      self.assertIn('--compact', cmd)
      self.assertNotIn('--jobs', cmd)
    for name in [a, b, c]:
      self.assertTrue(os.path.isfile(self.product(name)), name)
    self.assertEqual(self.sprite_make(self.target, '-z', '--jobs', '3', a, b, c), [])
    # The imports of a module are found through the path of the interpreter.
    curry.path.insert(0, self.tmpdir)
    self.addCleanup(
        lambda: self.tmpdir in curry.path and curry.path.remove(self.tmpdir)
      )
    module = curry.import_(a)
    self.assertEqual(list(curry.eval(module.goal, converter='topython')), [3])

  def test_width(self):
    '''At most N children run at once; independent modules run together.'''
    names = [self.write_module(i) for i in range(4)]
    running = []
    peak = []
    real_popen = subprocess.Popen
    def counting_popen(*args, **kwds):
      proc = real_popen(*args, **kwds)
      running.append(proc)
      alive = [p for p in running if p.poll() is None]
      peak.append(len(alive))
      return proc
    with self.currypath():
      with mock.patch.object(subprocess, 'Popen', counting_popen):
        make.main('sprite-make', [self.target, '-z', '--jobs', '2'] + names)
    self.assertEqual(len(running), 4)
    self.assertLessEqual(max(peak), 2)
    for name in names:
      self.assertTrue(os.path.isfile(self.product(name)), name)

  def test_serial_run_starts_no_child(self):
    '''Without --jobs, and with --jobs 1, the modules are made in this process.'''
    a = self.write_module(7)
    b = self.write_module(8)
    with self.currypath():
      with mock.patch.object(make, 'run_jobs', side_effect=AssertionError('a child started')):
        make.main('sprite-make', [self.target, '-z', a])
        make.main('sprite-make', [self.target, '-z', '--jobs', '1', b])
    self.assertTrue(os.path.isfile(self.product(a)))
    self.assertTrue(os.path.isfile(self.product(b)))

  def test_failed_import_stops_its_importers(self):
    '''
    A module whose child failed stops the modules that import it; with -k
    the others are still made.  The exit status is 1 either way.
    '''
    x = self.write_module(0, text='not a module')
    y = self.write_module(1, imports=[x])
    z = self.write_module(2)
    with contextlib.redirect_stderr(io.StringIO()) as stderr:
      with self.assertRaises(SystemExit) as cm:
        self.sprite_make(self.target, '-z', '-k', '--jobs', '3', x, y, z)
    self.assertEqual(cm.exception.code, 1)
    self.assertIn('%s was not made because an import failed' % y, stderr.getvalue())
    self.assertFalse(os.path.exists(self.product(y)))
    self.assertTrue(os.path.isfile(self.product(z)))
    w = self.write_module(3, imports=[x])
    with contextlib.redirect_stderr(io.StringIO()) as stderr:
      with self.assertRaises(SystemExit) as cm:
        self.sprite_make(self.target, '-z', '--jobs', '3', x, w)
    self.assertEqual(cm.exception.code, 1)
    self.assertIn('sprite-make:', stderr.getvalue())
    self.assertFalse(os.path.exists(self.product(w)))

  def test_output_is_made_here(self):
    '''
    With -o the named module is made in this process after its imports, so
    the output is copied as a serial run copies it.
    '''
    b = self.write_module(5)
    a = self.write_module(6, imports=[b])
    out = os.path.join(self.tmpdir, 'out' + self.suffix)
    commands = self.sprite_make(self.target, '-z', '--jobs', '2', '-o', out, a)
    self.assertEqual([cmd[-1] for cmd in commands], [b])
    self.assertTrue(os.path.isfile(out))
    self.assertTrue(os.path.isfile(self.product(a)))

  def test_plan_error_is_reported(self):
    '''
    An error while the plan is built gets the one-line report and the exit
    status 1 of every other error, with and without -k, instead of a
    traceback.
    '''
    a = self.write_module(11)
    for extra in [], ['-k']:
      with mock.patch.object(plans, 'makeplan', side_effect=RuntimeError('no plan today')):
        with self.currypath():
          with contextlib.redirect_stderr(io.StringIO()) as stderr:
            with self.assertRaises(SystemExit) as cm:
              make.main('sprite-make', [self.target, '-z'] + extra + [a])
      self.assertEqual(cm.exception.code, 1, extra)
      self.assertEqual(stderr.getvalue(), 'sprite-make: no plan today\n', extra)
    self.assertFalse(os.path.exists(self.product(a)))

  @unittest.skipIf(curry.flags['backend'] != 'cxx', 'the precompiled header belongs to the C++ backend')
  def test_header_is_built_before_the_children(self):
    '''
    A missing precompiled header is built once, in this process, before the
    first child starts, so the children find it instead of each building
    it.  The header lives in a directory of its own here, so the
    installation is not touched.
    '''
    from curry.backends.cxx import toolchain as cxx_toolchain
    root = os.path.join(self.tmpdir, 'pch')
    gchdir = os.path.join(root, cxx_toolchain.PrecompiledHeader.HEADER + '.gch')
    names = [self.write_module(i) for i in range(3)]
    builds = []
    real_build = cxx_toolchain.PrecompiledHeader.build
    def counting_build(pch):
      builds.append(pch.filename)
      return real_build(pch)
    module = config.python_package_name() + '.tools.make'
    members_at_start = []
    real_popen = subprocess.Popen
    def observing_popen(*args, **kwds):
      if args[0][1:3] == ['-m', module]:
        members_at_start.append(
            sorted(os.listdir(gchdir)) if os.path.isdir(gchdir) else []
          )
      return real_popen(*args, **kwds)
    with binding(os.environ, 'SPRITE_CXX_PCH_ROOT', root), self.currypath():
      with mock.patch.object(cxx_toolchain.PrecompiledHeader, 'build', counting_build):
        with mock.patch.object(subprocess, 'Popen', observing_popen):
          make.main('sprite-make', ['--so', '-z', '--jobs', '3'] + names)
    self.assertEqual(len(builds), 1, builds)
    member = os.path.basename(builds[0])
    self.assertTrue(os.path.isfile(os.path.join(gchdir, member)))
    self.assertEqual(members_at_start, [[member]] * 3)
    for name in names:
      self.assertTrue(os.path.isfile(self.product(name)), name)
    # The header is current: a second run over a new module builds nothing.
    b = self.write_module(12)
    with binding(os.environ, 'SPRITE_CXX_PCH_ROOT', root), self.currypath():
      with mock.patch.object(cxx_toolchain.PrecompiledHeader, 'build', counting_build):
        make.main('sprite-make', ['--so', '-z', '--jobs', '2', b])
    self.assertEqual(len(builds), 1)
    self.assertTrue(os.path.isfile(self.product(b)))
    # With the header disabled nothing is built and nothing is yielded.
    with binding(os.environ, 'SPRITE_CXX_PCH_ROOT', ''):
      step = cxx_toolchain.Cpp2So(curry.getInterpreter())
      self.assertFalse(step.prepare_header())
      self.assertEqual(list(step._pchflags()), [])

  @unittest.skipIf(curry.flags['backend'] != 'py', 'the bytecode cache belongs to the Python backend')
  def test_current_module_gets_its_bytecode(self):
    '''A named module that is current already gets a missing bytecode cache without a child.'''
    from curry.backends.py import toolchain as py_toolchain
    a = self.write_module(9)
    self.sprite_make('--py', '-z', '--jobs', '2', a)
    cache = py_toolchain.bytecode_file(self.product(a))
    os.unlink(cache)
    self.assertEqual(self.sprite_make('--py', '-z', '--jobs', '2', a), [])
    self.assertTrue(os.path.isfile(cache))


# A child that holds the lock of a module until it reads a line.
HOLDER = r'''
import sys
from curry.toolchain import _productlock
with _productlock.locked(sys.argv[1]) as waited:
  print('held', waited, flush=True)
  sys.stdin.readline()
print('released', flush=True)
'''

class TestProductLock(cytest.TestCase):
  '''
  The lock of the products of a module (curry.toolchain._productlock): two
  processes that compile one module into one product directory take turns,
  and the second compiles nothing when the first wrote a current object.
  '''
  TIMEOUT = 300

  def setUp(self):
    super().setUp()
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-lock-')
    self.addCleanup(shutil.rmtree, self.tmpdir, True)
    self.name = 'LockedModule'
    self.curryfile = os.path.join(self.tmpdir, self.name + '.curry')
    self.lock = os.path.join(self.tmpdir, SUBDIR, self.name + '.lock')

  def held(self):
    '''Whether another open file description holds the lock.'''
    fd = os.open(self.lock, os.O_RDWR)
    try:
      fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
      return True
    else:
      return False
    finally:
      os.close(fd)

  def test_lockfile(self):
    subdir = os.path.join(self.tmpdir, SUBDIR)
    for filename in [
        self.curryfile
      , os.path.join(subdir, self.name + '.icy')
      , os.path.join(subdir, self.name + '.json.z')
      , os.path.join(subdir, self.name + '.cpp')
      , os.path.join(subdir, self.name + '.so')
      ]:
      self.assertEqual(_productlock.lockfile(filename), self.lock, filename)

  def test_free_lock(self):
    # The lock file and its directory are made; the lock is held for the
    # duration of the context, once per process (re-entrant), and released
    # with it.
    self.assertFalse(os.path.exists(self.lock))
    with _productlock.locked(self.curryfile) as waited:
      self.assertFalse(waited)
      self.assertTrue(os.path.isfile(self.lock))
      self.assertTrue(self.held())
      with _productlock.locked(self.curryfile) as again:
        self.assertFalse(again)
        self.assertTrue(self.held())
      self.assertTrue(self.held())
    self.assertFalse(self.held())
    self.assertTrue(os.path.isfile(self.lock))

  def test_waits_for_another_process(self):
    # A child holds the lock; a thread of this process waits for it and
    # says so.  The thread does not return before the child releases.
    child = subprocess.Popen(
        [sys.executable, '-B', '-c', HOLDER, self.curryfile]
      , stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
      , env=dict(os.environ, PYTHONIOENCODING='utf-8')
      )
    try:
      self.assertEqual(child.stdout.readline().split(), ['held', 'False'])
      self.assertTrue(self.held())
      result = {}
      def take():
        with _productlock.locked(self.curryfile) as waited:
          result['waited'] = waited
          result['held_by_child'] = child.poll() is None
      thread = threading.Thread(target=take)
      thread.start()
      thread.join(1.0)
      self.assertTrue(thread.is_alive(), 'the lock was not waited for')
      child.stdin.write('go\n')
      child.stdin.close()
      thread.join(self.TIMEOUT)
      self.assertFalse(thread.is_alive())
      self.assertIs(result['waited'], True)
      self.assertEqual(child.wait(self.TIMEOUT), 0)
      self.assertEqual(child.stdout.readline().strip(), 'released')
    finally:
      if child.poll() is None:
        child.kill()
        child.wait()
      child.stdout.close()
      if not child.stdin.closed:
        child.stdin.close()

  def test_no_lock_in_an_unwritable_directory(self):
    # Nothing can be compiled into the directory; the steps say so, and
    # the lock neither fails nor makes the directory.
    if os.geteuid() == 0:
      self.skipTest('root writes anywhere')
    os.chmod(self.tmpdir, 0o500)
    self.addCleanup(os.chmod, self.tmpdir, 0o700)
    with _productlock.locked(self.curryfile) as waited:
      self.assertFalse(waited)
    self.assertFalse(os.path.exists(os.path.join(self.tmpdir, '.curry')))

  def test_no_lock_without_flock(self):
    # A file system that refuses flock (ENOLCK, a network file system
    # without a lock service): no lock, and the compile runs unlocked, as
    # before the lock.  Before, the error ended the compile at its first
    # step (here the JSON of an ICurry file, which needs no front end).
    subdir = os.path.join(self.tmpdir, SUBDIR)
    os.makedirs(subdir)
    shutil.copy(
        os.path.join('data', 'curry', SUBDIR, 'hello.icy'), subdir
      )
    lock = os.path.join(subdir, 'hello.lock')
    error = OSError(errno.ENOLCK, 'No locks available')
    with mock.patch.object(_productlock.fcntl, 'flock', side_effect=error):
      with _productlock.locked(self.curryfile) as waited:
        self.assertFalse(waited)
        self.assertTrue(os.path.isfile(self.lock))
        self.assertNotIn(self.lock, _productlock._held)
      plan = plans.makeplan(
          None, plans.MAKE_ICURRY | plans.MAKE_JSON | plans.ZIP_JSON
        )
      product = toolchain.makecurry(plan, 'hello', [self.tmpdir])
    self.assertEqual(product, os.path.join(subdir, 'hello.json.z'))
    self.assertTrue(os.path.isfile(product))
    self.assertTrue(os.path.isfile(lock))
    self.assertFalse(self.held())

  @unittest.skipIf(
      curry.flags['backend'] != 'cxx' or config.cxx_tool() is None
    , 'the compile needs the C++ backend and its compiler'
    )
  @cytest.skipIfInterpreted('the test reads the object it compiled')
  def test_two_compiles_write_one_object(self):
    '''
    Two sprite-make --so of one module at once: both end well, one of them
    compiles, and the object, its stamp and the generated file are whole.
    The lock is held here while the two start, so both find it taken and
    both wait; the first to get it compiles, and the second finds the
    object current and compiles nothing.  Without the lock both wrote the
    generated file and the object in place at once (the Quickstart told
    the reader to wait for the background compile).
    '''
    from curry.backends.cxx.toolchain import Cpp2So
    subdir = os.path.join(self.tmpdir, SUBDIR)
    os.makedirs(subdir)
    with open(os.path.join(subdir, self.name + '.json.z'), 'wb') as stream:
      stream.write(zlib.compress(cytest.json_module(self.name, 7).encode('utf-8')))
    env = dict(
        os.environ, CURRYPATH=self.tmpdir, SPRITE_LOG_LEVEL='INFO'
      , SPRITE_PRODUCT_CACHE=''
      )
    cmd = [
        'prlimit', '--as=%d' % (2 << 30), 'timeout', str(self.TIMEOUT)
      , config.installed_path('bin', 'sprite-make'), '--so', '-z', self.name
      ]
    with _productlock.locked(self.curryfile):
      children = [
          subprocess.Popen(
              cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            , text=True
            )
          for _ in range(2)
        ]
      # Both children reach the lock while it is held here.
      time.sleep(2.0)
    outputs = [child.communicate(timeout=self.TIMEOUT) for child in children]
    for child, (out, err) in zip(children, outputs):
      self.assertEqual(child.returncode, 0, out + err)
    sofile = os.path.join(subdir, self.name + '.so')
    cppfile = os.path.join(subdir, self.name + '.cpp')
    self.assertTrue(os.path.isfile(sofile))
    self.assertTrue(os.path.isfile(cppfile))
    cpp2so = Cpp2So(curry.getInterpreter())
    self.assertTrue(cpp2so.stamp_is_current(sofile))
    self.assertFalse(cpp2so.is_stale(sofile))
    self.assertFalse(cpp2so.is_stale(cppfile))
    logs = [err for _, err in outputs]
    compiled = sum(
        line.count('Compiling ') for log in logs for line in log.splitlines()
        if self.name + ".so'" in line
      )
    self.assertEqual(compiled, 1, logs)
    waited = sum(
        'Waiting for another process that compiles' in log for log in logs
      )
    self.assertGreaterEqual(waited, 1, logs)
    # The object is whole: it loads and runs.
    M = curry.load(sofile)
    self.assertEqual(
        list(curry.eval(M.goal, converter='topython')), [7]
      )


class TestProgramDirectory(cytest.TestCase):
  '''
  A program given as a file has its directory searched first, as PAKCS
  searches (toolchain._findcurry.program_path): sprite-make --so
  Second.curry beside Smoke.curry failed with "Curry module 'Smoke' not
  found" unless CURRYPATH named the directory (the environment test of the
  conda lane, 2026-10-08).  The two modules here live in a directory that
  no CURRYPATH names, and the tools run from another directory.
  '''
  TIMEOUT = 300

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    if config.curry_frontend() is None:
      raise unittest.SkipTest('the Curry front end is not configured')

  def setUp(self):
    super().setUp()
    self.tmpdir = tempfile.mkdtemp(prefix='sprite-progdir-')
    self.addCleanup(shutil.rmtree, self.tmpdir, True)
    self.progdir = os.path.join(self.tmpdir, 'prog')
    self.cwd = os.path.join(self.tmpdir, 'elsewhere')
    os.makedirs(self.progdir)
    os.makedirs(self.cwd)
    with open(os.path.join(self.progdir, 'ProgDirLib.curry'), 'w') as stream:
      stream.write('module ProgDirLib where\n\ntwice :: Int -> Int\ntwice x = x + x\n')
    self.program = os.path.join(self.progdir, 'ProgDirMain.curry')
    with open(self.program, 'w') as stream:
      stream.write(
          'module ProgDirMain where\nimport ProgDirLib\n\n'
          'main :: Int\nmain = twice 4\n'
        )
    self.env = dict(os.environ)
    self.env.pop('CURRYPATH', None)
    if curry.flags['backend'] == 'cxx':
      # The children load the objects they compile.  Under the runner's
      # interpret:all a load is refused, so the children run under the
      # tiered default, as the loader tests do.
      self.env['SPRITE_INTERPRETER_FLAGS'] = 'backend:cxx,interpret:tiered'

  def run_tool(self, tool, *args):
    cmd = [
        'prlimit', '--as=%d' % (2 << 30), 'timeout', str(self.TIMEOUT)
      , config.installed_path('bin', tool)
      ] + list(args)
    return subprocess.run(
        cmd, env=self.env, cwd=self.cwd, capture_output=True, text=True
      )

  def sofile(self, name):
    return os.path.join(self.progdir, SUBDIR, name + '.so')

  def test_sprite_exec(self):
    proc = self.run_tool('sprite-exec', self.program)
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    self.assertEqual(proc.stdout.split(), ['8'])

  @unittest.skipIf(
      curry.flags['backend'] != 'cxx' or config.cxx_tool() is None
    , 'the compile needs the C++ backend and its compiler'
    )
  def test_sprite_make_so(self):
    # The compile, a run from the objects, and a second compile that finds
    # them current (the plan imports the import to judge the object).
    proc = self.run_tool('sprite-make', '--so', self.program)
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    self.assertTrue(os.path.isfile(self.sofile('ProgDirMain')))
    self.assertTrue(os.path.isfile(self.sofile('ProgDirLib')))
    proc = self.run_tool('sprite-exec', self.program)
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    self.assertEqual(proc.stdout.split(), ['8'])
    stamp = os.stat(self.sofile('ProgDirMain')).st_mtime_ns
    proc = self.run_tool('sprite-make', '--so', self.program)
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    self.assertEqual(os.stat(self.sofile('ProgDirMain')).st_mtime_ns, stamp)
    # curry.load of the object imports the import from beside the source.
    code = (
        'import curry\n'
        'M = curry.load(%r)\n'
        'print(list(curry.eval(M.main, converter="topython")))\n'
      ) % self.sofile('ProgDirMain')
    proc = subprocess.run(
        [sys.executable, '-B', '-c', code], env=self.env, cwd=self.cwd
      , capture_output=True, text=True
      )
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    self.assertEqual(proc.stdout.strip(), '[8]')

  def test_import_by_name_with_a_path(self):
    # A module given by name with an explicit currypath is found on that
    # path alone, and its imports are searched on the path of the
    # interpreter, as before: the import beside it is not found.  The
    # directory of a program comes first for a program given as a file
    # (test_import_of_a_path), not for a name.
    code = (
        'import curry\n'
        'from curry.exceptions import ModuleLookupError\n'
        'try:\n'
        '  curry.import_("ProgDirMain", currypath=[%r])\n'
        'except ModuleLookupError as exc:\n'
        '  print("ModuleLookupError", "ProgDirLib" in str(exc))\n'
      ) % self.progdir
    proc = subprocess.run(
        [sys.executable, '-B', '-c', code], env=self.env, cwd=self.cwd
      , capture_output=True, text=True
      )
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    self.assertEqual(proc.stdout.split(), ['ModuleLookupError', 'True'])

  def test_import_of_a_path(self):
    # curry.import_ of a path, with the directory on no search path.
    code = (
        'import curry\n'
        'M = curry.import_(%r, is_sourcefile=True)\n'
        'print(list(curry.eval(M.main, converter="topython")))\n'
        'print(curry.import_(%r) is M)\n'
      ) % (self.program, 'ProgDirMain')
    proc = subprocess.run(
        [sys.executable, '-B', '-c', code], env=self.env, cwd=self.cwd
      , capture_output=True, text=True
      )
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    self.assertEqual(proc.stdout.split(), ['[8]', 'True'])
    if curry.flags['backend'] == 'cxx' and config.cxx_tool() is not None:
      # The compile on first use (interpret:off) imports the import from
      # beside the program as well.
      env = dict(self.env, SPRITE_INTERPRETER_FLAGS='backend:cxx,interpret:off')
      proc = subprocess.run(
          [sys.executable, '-B', '-c', code], env=env, cwd=self.cwd
        , capture_output=True, text=True
        )
      self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
      self.assertEqual(proc.stdout.split(), ['[8]', 'True'])

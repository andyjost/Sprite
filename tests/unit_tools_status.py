'''The tools own answer lines and exit statuses; Python keeps Results.'''
import cytest # from ./lib; must be first
from curry import config
import curry, os, selectors, shutil, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(ROOT, 'data', 'curry', 'flows', 'Tools.curry')
BOUNDARY = os.path.join(ROOT, 'data', 'boundary', '51-tools-parity')
TIMEOUT = 120


class TestToolsStatus(cytest.TestCase):
  def child(self, command, text=None, cwd=None):
    return subprocess.run(command, input=text, capture_output=True, text=True,
        cwd=cwd, timeout=TIMEOUT)

  def tool(self, tool, goal, source=TOOLS):
    if tool == 'exec':
      command = [config.sprite_exec(), source, '-g', goal]
    else:
      command = [sys.executable, '-m', 'curry.tools.icy',
          ':load', source, ':eval', goal, ':quit']
    return self.child(command)

  def check(self, proc, status, out, err=''):
    self.assertEqual((proc.returncode, proc.stdout, proc.stderr),
        (status, out, err))

  def test_python_module_starts_repl(self):
    self.check(self.child([sys.executable, '-m', 'curry'], ':quit\n'),
        0, 'Prelude> ')

  def test_sprite_exec_starts_repl(self):
    self.check(self.child([config.sprite_exec()], ':quit\n'), 0, 'Prelude> ')

  def test_python_module_runs_program(self):
    self.check(self.child([sys.executable, '-m', 'curry', TOOLS]), 0, '1\n2\n')

  def test_answer_lines_and_statuses(self):
    cases = [
        ('main', 0, '1\n2\n', '')
      , ('nothing', 2, '*** No value found!\n', '')
      , ('boom', 1, '', 'ERROR: boom\n')
      , ('suspend', 1, '', '*** Evaluation suspended!\n')
      , ('hello', 0, 'hello\n', '')
      , ('return ()', 0, '', '')
      , ('return 5', 0, '5\n', '')
      , ('()', 0, '()\n', '')
      , ('xs ++ [3] =:= [1,2,3] where xs free', 0, '{xs=[1,2]} True\n', '')
      , ('main + 10', 0, '11\n12\n', '')
      , ('1 ? error "boom" :: Int', 1, '1\n', 'ERROR: boom\n')
      , ('True ? suspend', 1, 'True\n', '*** Evaluation suspended!\n')
      ]
    for tool in ('exec', 'repl'):
      for goal, status, out, err in cases:
        with self.subTest(tool=tool, goal=goal):
          self.check(self.tool(tool, goal), status, out, err)

  def test_answers_precede_errors_on_a_merged_pipe(self):
    goal = '1 ? error "boom" :: Int'
    for command in ([config.sprite_exec(), TOOLS, '-g', goal],
        [sys.executable, '-m', 'curry.tools.icy', ':load', TOOLS,
            ':eval', goal, ':quit']):
      with self.subTest(command=command[0]):
        proc = subprocess.run(command, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, timeout=TIMEOUT)
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertEqual(proc.stdout, '1\nERROR: boom\n')

  @cytest.skipUnlessObjectsLoad('a saved program loads its object')
  def test_saved_program_answers_and_io_unit(self):
    module = curry.import_(TOOLS)
    with tempfile.TemporaryDirectory() as directory:
      program = os.path.join(directory, 'tools.exe')
      for name, output in [('main', '1\n2\n'), ('hello', 'hello\n')]:
        with self.subTest(goal=name):
          curry.save(module, program, main=module[name])
          self.check(self.child([program]), 0, output)

  def test_help_and_string_spacing(self):
    for command in ([config.sprite_exec(), '--help'],
        [sys.executable, '-m', 'curry.tools.icy', '--help']):
      proc = self.child(command)
      self.assertEqual(proc.returncode, 0, proc.stderr)
      helptext = ' '.join(proc.stdout.split())
      self.assertIn('No value found!', helptext)
      self.assertIn('Evaluation suspended!', helptext)
    proc = self.child([sys.executable, '-m', 'curry.tools.icy'],
        ':eva putStrLn "a   b"\n:quit\n')
    self.check(proc, 0, 'Prelude> a   b\nPrelude> ')

  def test_compile_errors(self):
    for tool in ('exec', 'repl'):
      with self.subTest(tool=tool):
        proc = self.tool(tool, ')')
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(proc.stdout, '')
        self.assertRegex(proc.stderr, r'^ERROR: [^/\n]*Error:.*\n$')
        self.assertNotIn('Traceback', proc.stderr)
    with tempfile.TemporaryDirectory() as directory:
      source = os.path.join(directory, 'Broken.curry')
      with open(source, 'w') as stream:
        stream.write('module Broken where\nmain = )\n')
      for tool in ('exec', 'repl'):
        with self.subTest(tool=tool, file=True):
          proc = self.tool(tool, 'main', source=source)
          self.assertEqual(proc.returncode, 1)
          self.assertEqual(proc.stdout, '')
          self.assertRegex(proc.stderr, r'^ERROR: Broken.curry:2:\d+.*Error:.*\n$')
          self.assertNotIn(directory, proc.stderr)

  def test_prompt_keeps_session_after_error(self):
    proc = self.child([sys.executable, '-m', 'curry.tools.icy'],
        ':eval error "boom" :: Int\n:type 1\n:eval 42\n:quit\n')
    self.check(proc, 0, 'Prelude> Prelude> 1 :: Num a => a\n'
        'Prelude> 42\nPrelude> ', 'ERROR: boom\n')
    for goal, status, err in [
        ('failed :: Int', 2, '')
      , ('error "boom" :: Int', 1, 'ERROR: boom\n')
      , ('x == (1 :: Int) where x free', 1, '*** Evaluation suspended!\n')
      ]:
      with self.subTest(goal=goal):
        proc = self.child([sys.executable, '-m', 'curry.tools.icy'],
            goal + '\n:quit\n')
        self.assertEqual(proc.returncode, status)
        self.assertEqual(proc.stderr, err)

  def test_flags_and_reload(self):
    proc = self.child([sys.executable, '-m', 'curry.tools.icy',
        ':set', 'interpret', 'new', ':load', TOOLS, ':set', 'inline_budget', '0',
        ':set', 'rotation', 'steps:200', ':set', '+checker',
        ':reload', ':eval', 'main', ':quit'])
    self.check(proc, 0, '1\n2\n')
    proc = self.child([sys.executable, '-m', 'curry.tools.icy',
        ':set', 'bogus', '1', ':quit'])
    self.check(proc, 1, '', "ERROR: 'bogus' is not a flag; the flags are "
        + ', '.join(curry.flags) + '\n')
    proc = self.child([sys.executable, '-m', 'curry.tools.icy',
        ':set', 'inline_budget', 'bad', ':quit'])
    self.check(proc, 1, '', "ERROR: 'bad' is not a value for flag "
        "'inline_budget'; expected an integer\n")

  def test_reload_reads_edits_and_keeps_code_after_refusal(self):
    with tempfile.TemporaryDirectory() as directory:
      source = os.path.join(directory, 'ReloadTool.curry')
      def write(body):
        with open(source, 'w') as stream:
          stream.write('module ReloadTool where\nvalue :: Int\n' + body + '\n')
      write('value = 1')
      proc = subprocess.Popen([sys.executable, '-m', 'curry.tools.icy',
          ':set', 'interpret', 'new', ':load', source],
          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      def prompt():
        output = b''
        with selectors.DefaultSelector() as selector:
          selector.register(proc.stdout, selectors.EVENT_READ)
          while not output.endswith(b'ReloadTool> '):
            self.assertTrue(selector.select(TIMEOUT), 'prompt timed out')
            part = os.read(proc.stdout.fileno(), 4096)
            self.assertTrue(part, 'REPL ended before the prompt')
            output += part
        return output.decode()
      try:
        self.assertEqual(prompt(), 'ReloadTool> ')
        write('value = 2')
        proc.stdin.write(b':reload\n')
        proc.stdin.flush()
        self.assertEqual(prompt(), 'ReloadTool> ')
        proc.stdin.write(b':eval value\n')
        proc.stdin.flush()
        self.assertEqual(prompt(), '2\nReloadTool> ')
        write('value = )')
        out, err = proc.communicate(b':reload\n:eval value\n:quit\n', timeout=TIMEOUT)
        self.assertEqual(proc.returncode, 0, err.decode())
        self.assertEqual(out.decode(), 'ReloadTool> 2\nReloadTool> ')
        diagnostics = err.decode().splitlines()
        self.assertEqual(len(diagnostics), 2, diagnostics)
        self.assertRegex(diagnostics[0], r'^ERROR: ReloadTool.curry:\d+:\d+.*Error:')
        self.assertTrue(diagnostics[1].startswith("WARNING: module 'ReloadTool' was not read again:"))
        self.assertNotIn(directory, err.decode())
      finally:
        if proc.poll() is None:
          proc.kill()
        proc.communicate()

  def test_diagnostics_hide_directories(self):
    with tempfile.TemporaryDirectory() as directory:
      missing = os.path.join(directory, 'Missing.curry')
      for tool in ('exec', 'repl'):
        with self.subTest(tool=tool):
          proc = self.tool(tool, 'main', source=missing)
          self.assertEqual(proc.returncode, 1)
          self.assertNotIn(directory, proc.stderr)
          self.assertNotIn('Traceback', proc.stderr)
      make = config.installed_path('bin', 'sprite-make')
      proc = self.child([make, '--icy', missing])
      self.assertEqual(proc.returncode, 1)
      self.assertNotIn(directory, proc.stderr)
      self.assertNotIn('Traceback', proc.stderr)

  def test_type_uses_typeof(self):
    proc = self.child([sys.executable, '-m', 'curry.tools.icy',
        ':type', '1+2', ':quit'])
    self.check(proc, 0, '1+2 :: ' + curry.typeof(curry.parse('1+2')) + '\n')

  def test_oracle_answer_lines(self):
    pakcs = config.installed_path('tools', 'pakcs')
    if not os.path.isfile(pakcs):
      pakcs = shutil.which('pakcs')
    if not pakcs or not os.access(pakcs, os.X_OK):
      self.skipTest('PAKCS is unavailable; tool parity was not compared')
    source = os.path.join(BOUNDARY, 'Tools.curry')
    for goal in ('coin', 'three', 'nothing', 'rule "a" ins where ins free'):
      oracle = self.child([os.path.join(ROOT, 'oracle'), 'Tools', goal], cwd=BOUNDARY)
      self.assertEqual(oracle.returncode, 0, oracle.stderr)
      for tool in ('exec', 'repl'):
        with self.subTest(tool=tool, goal=goal):
          proc = self.tool(tool, goal, source=source)
          self.assertEqual(proc.returncode, 2 if goal == 'nothing' else 0, proc.stderr)
          answers = proc.stdout.replace('*** No value found!\n', '')
          self.assertEqual(answers, oracle.stdout)
    oracle = self.child([os.path.join(ROOT, 'oracle_type'), 'Tools', 'coin'], cwd=BOUNDARY)
    self.assertEqual(oracle.returncode, 0, oracle.stderr)
    proc = self.child([sys.executable, '-m', 'curry.tools.icy',
        ':load', source, ':type', 'coin', ':quit'])
    self.check(proc, 0, 'coin :: ' + oracle.stdout)


if __name__ == '__main__':
  unittest.main()

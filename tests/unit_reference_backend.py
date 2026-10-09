'''
The reference backend behind the flag backend:py (issue #82, stage 5).  The
user guide and the READMEs a user reads name no Python backend; the
developer notes name the flag, what the backend is for and its limits; and
the flag still selects the backend through the surfaces the test suite, CI
and the examples use.
'''
import cytest # from ./lib; must be first
from curry import config
from curry.interpreter import Interpreter
import curry, glob, os, re, subprocess, sys, unittest

ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
  )
DOCS = os.path.join(ROOT, 'docs', 'source')
# The READMEs a user reads: the README of the repository, examples/README and
# the README of every example.  The files a developer reads (README.contrib,
# tests/README, conda/README.md, curry/README.md, the READMEs under src/ and
# under tests/data/) are allowed to name the backend and are not scanned.
USER_READMES = ['README', 'README.md', 'examples/README', 'examples/*/README']
# The developer pages name the backend; the user guide is every other page.
DEVELOPER_PAGES = ('DeveloperNotes.rst', 'DeveloperSetup.rst')
# The generated pages, which the build of the documentation writes from the
# installation: the usage and manual pages of the tools and the API reference.
GENERATED = re.compile(r'(-usage|-man)\.rst$|^Reference/curry\..+\.rst$')
# The words and flags that name the Python backend.  A space matches a line
# break too, so a phrase split over two lines is found.
PATTERNS = [
    r'[Pp]ython backend', r'backend:py\b', r'backend py\b', r'-b py\b'
  , r"'py'", r'``py``', r'backends\.py\b', r'py\|cxx', r'py or cxx'
  , r'--py\b', r'--python\b', r'both backends', r'[Pp]ython form'
  , r'generated [Pp]ython', r'[Pp]ython mode', r'[Pp]ython target'
  ]
TIMEOUT = 120

def findall(text, patterns):
  '''Yields (lineno, line) for every match of the patterns in the text.'''
  for pattern in patterns:
    for match in re.finditer(pattern.replace(' ', r'\s+'), text):
      lineno = text.count('\n', 0, match.start()) + 1
      yield lineno, text.splitlines()[lineno - 1]

class TestUserGuide(cytest.TestCase):
  def pages(self):
    for path in sorted(glob.glob(os.path.join(DOCS, '**', '*.rst'), recursive=True)):
      rel = os.path.relpath(path, DOCS)
      if os.path.basename(rel) in DEVELOPER_PAGES or GENERATED.search(rel):
        continue
      yield rel, path

  def readmes(self):
    for pattern in USER_READMES:
      for path in sorted(glob.glob(os.path.join(ROOT, pattern))):
        yield os.path.relpath(path, ROOT), path

  def test_user_guide_names_no_python_backend(self):
    '''No page of the user guide names the Python backend or its flag.'''
    hits = []
    pages = 0
    for rel, path in self.pages():
      pages += 1
      with open(path, encoding='utf-8') as stream:
        text = stream.read()
      for lineno, line in sorted(set(findall(text, PATTERNS))):
        hits.append('%s:%d: %s' % (rel, lineno, line.rstrip()))
    self.assertGreater(pages, 20)
    self.assertEqual(hits, [], 'the user guide names the Python backend:\n'
                               + '\n'.join(hits))

  def test_readmes_name_no_python_backend(self):
    '''No README a user reads names the Python backend or its flag.'''
    hits = []
    files = 0
    for rel, path in self.readmes():
      files += 1
      with open(path, encoding='utf-8') as stream:
        text = stream.read()
      for lineno, line in sorted(set(findall(text, PATTERNS))):
        hits.append('%s:%d: %s' % (rel, lineno, line.rstrip()))
    self.assertGreater(files, 20)
    self.assertEqual(hits, [], 'a README names the Python backend:\n'
                               + '\n'.join(hits))

  def test_developer_notes_name_the_flag(self):
    '''The developer notes name the flag, the purpose and the gate.'''
    with open(os.path.join(DOCS, 'DeveloperNotes.rst'), encoding='utf-8') as stream:
      text = stream.read()
    for needle in [
        'backend:py', 'sprite-exec -b py', ':set backend py'
      , "Interpreter(flags={'backend': 'py'})", 'reference implementation'
      , 'removal gate', '#82', 'recursion_limit', 'step_budget'
      , 'curry.save', 'cytest.step'
      ]:
      self.assertIn(needle, text)
    with open(os.path.join(DOCS, 'index.rst'), encoding='utf-8') as stream:
      self.assertIn('DeveloperNotes', stream.read())


class TestFlag(cytest.TestCase):
  '''backend:py selects the reference backend; the help texts omit the value.'''

  def test_interpreter_argument(self):
    interp = Interpreter(flags={'backend': 'py'})
    self.assertEqual(interp.flags['backend'], 'py')
    self.assertEqual(interp.backend.backend_name, 'py')
    value, = interp.eval(interp.expr(interp.prelude.id, 1))
    self.assertEqual(str(value), '1')

  def test_environment_variable(self):
    code = '''
import os
os.environ['SPRITE_INTERPRETER_FLAGS'] = 'backend:py'
import curry
print(curry.flags['backend'], curry.getInterpreter().backend.backend_name)
'''
    proc = cytest.run_in_subprocess(code, TIMEOUT)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout.split(), ['py', 'py'])

  def test_sprite_exec_option(self):
    '''-b py selects it; the help names no value of -b.'''
    env = dict(os.environ)
    env.pop('SPRITE_INTERPRETER_FLAGS', None)
    proc = subprocess.run(
        ['timeout', str(TIMEOUT), config.sprite_exec(), '-h']
      , capture_output=True, text=True, env=env
      )
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertIn('--backend BACKEND', proc.stdout)
    self.assertNotIn('{py,cxx}', proc.stdout)
    self.assertNotIn('{cxx,py}', proc.stdout)
    proc = subprocess.run(
        ['timeout', str(TIMEOUT), config.sprite_exec(), '-b', 'py']
      , input="print('backend', __package__.flags['backend'])\n"
      , capture_output=True, text=True, env=env
      )
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertIn('backend py', proc.stdout)
    # The error for an unknown value names no value.
    proc = subprocess.run(
        ['timeout', str(TIMEOUT), config.sprite_exec(), '-b', 'foo', os.devnull]
      , capture_output=True, text=True, env=env
      )
    self.assertNotEqual(proc.returncode, 0)
    self.assertIn("unknown backend 'foo'", proc.stderr)
    self.assertNotIn("'py'", proc.stderr)
    self.assertNotIn('choose from', proc.stderr)

  def test_sprite_make_option(self):
    '''--py works; the help and the manual of sprite-make name no Python target.'''
    make = os.path.join(os.path.dirname(config.sprite_exec()), 'sprite-make')
    for option in ['-h', '--man']:
      proc = subprocess.run(
          ['timeout', str(TIMEOUT), make, option], capture_output=True, text=True
        )
      self.assertEqual(proc.returncode, 0, proc.stderr)
      for lineno, line in findall(proc.stdout, PATTERNS):
        self.fail('sprite-make %s names the Python backend: %r' % (option, line))
      self.assertNotIn('--py', proc.stdout)
      self.assertNotIn('-p,', proc.stdout)
    self.assertIn('goal of a generated program', proc.stdout)
    proc = subprocess.run(
        ['timeout', str(TIMEOUT), make, '-h'], capture_output=True, text=True
      )
    self.assertIn('--goal GOAL', proc.stdout)
    # The error for a missing target names the option of no backend.
    proc = subprocess.run(
        ['timeout', str(TIMEOUT), make, 'Prelude'], capture_output=True, text=True
      )
    self.assertEqual(proc.returncode, 1)
    self.assertIn('--so must be supplied', proc.stderr)
    self.assertNotIn('--py', proc.stderr)
    # The hidden option still parses (-S prints the subdirectory and exits).
    for option in ['-p', '--py', '--python']:
      proc = subprocess.run(
          ['timeout', str(TIMEOUT), make, option, '-S'], capture_output=True, text=True
        )
      self.assertEqual(proc.returncode, 0, proc.stderr)
      self.assertIn('.curry', proc.stdout)

  def test_repl_option(self):
    '''The listing of :set describes the option without naming the value.'''
    proc = subprocess.run(
        [ 'timeout', str(TIMEOUT), sys.executable, '-m', 'curry.tools.icy'
        , ':set', ':quit'
        ]
      , capture_output=True, text=True
      )
    self.assertEqual(proc.returncode, 0, proc.stderr)
    listing = proc.stdout + proc.stderr
    self.assertRegex(listing, r'backend\s+- The backend of the session\.  Setting it reloads')
    self.assertNotIn('py or cxx', listing)
    self.assertIn("backend : %r" % curry.flags['backend'], listing)
    # The error for an unknown value names no value.
    proc = subprocess.run(
        [ 'timeout', str(TIMEOUT), sys.executable, '-m', 'curry.tools.icy'
        , ':set', 'backend', 'foo', ':quit'
        ]
      , capture_output=True, text=True
      )
    self.assertIn("Invalid backend: 'foo'.", proc.stderr)
    self.assertNotIn("'py'", proc.stderr)
    self.assertNotIn('Expected one of', proc.stderr)
